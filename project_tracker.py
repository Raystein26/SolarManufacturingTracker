import os
import logging
import time
import datetime
import sys
import threading
from app import app, db
from models import Project, Source, NewsArticle, ScrapeLog
from scraper import fetch_news_from_source, extract_article_content, extract_project_data
from progress_tracker import progress

logger = logging.getLogger(__name__)

# List of reputable sources for renewable energy projects in India
DEFAULT_SOURCES = [
    "https://mercomindia.com/",
    "https://www.pv-magazine-india.com/",
    "https://jmkresearch.com/",
    "https://www.pv-tech.org/",
    "https://energy.economictimes.indiatimes.com/",
    "https://www.business-standard.com/industry/news/power",
    "https://www.livemint.com/industry/energy",
    "https://www.solarquarter.com/",
    "https://www.financialexpress.com/industry/",
    "https://www.thehindubusinessline.com/economy/",
    "https://www.renews.biz/regions/india/",
    "https://indianexpress.com/section/business/",
    "https://www.eqmagpro.com/",
    "https://www.cnbctv18.com/cleantech/",
    "https://economictimes.indiatimes.com/industry/renewables",
    "https://www.moneycontrol.com/news/business/economy/energy",
    "https://www.bloomberg.com/news/topics/sustainable-energy",
    "https://pib.gov.in/indexd.aspx"
]

def initialize_sources():
    """Initialize the database with default sources if empty or update with new sources"""
    # Ensure we have the app context
    with app.app_context():
        try:
            # First, get all existing sources URLs
            existing_urls = {source.url for source in Source.query.all()}
            new_sources_added = 0
            
            # Log the action
            logger.info(f"Initializing sources. Found {len(existing_urls)} existing sources.")
            logger.info(f"Default sources list contains {len(DEFAULT_SOURCES)} sources.")
            
            # Add each source from DEFAULT_SOURCES if it doesn't exist yet
            for url in DEFAULT_SOURCES:
                if url not in existing_urls:
                    # Extract domain name for the source name
                    domain = url.split("//")[-1].split("/")[0]
                    if domain.startswith('www.'):
                        domain = domain[4:]
                    name = ' '.join(word.capitalize() for word in domain.split('.')[0].split('-'))
                    
                    # Create a description based on the site
                    if 'bloomberg' in url:
                        description = "International business and finance news covering renewable energy sector"
                    elif 'economictimes' in url:
                        description = "Economic Times coverage of renewable energy sector in India"
                    elif 'pib.gov.in' in url:
                        description = "Press Information Bureau of the Government of India"
                    elif 'moneycontrol' in url:
                        description = "Business and market news covering energy sector in India"
                    else:
                        description = f"News source for renewable energy projects in India: {url}"
                    
                    # Create the new source object
                    new_source = Source(
                        url=url,
                        name=name,
                        description=description,
                        created_at=datetime.datetime.utcnow()
                    )
                    
                    logger.info(f"Adding new source: {name} - {url}")
                    db.session.add(new_source)
                    new_sources_added += 1
            
            # Commit all new sources to the database
            if new_sources_added > 0:
                db.session.commit()
                logger.info(f"Added {new_sources_added} new sources to the database")
            else:
                logger.info(f"No new sources to add")
                
            # If database was completely empty and we added sources, log it
            source_count = Source.query.count()
            if source_count == new_sources_added and new_sources_added > 0:
                logger.info(f"Initialized database with {source_count} default sources")
                
            return new_sources_added
        except Exception as e:
            logger.error(f"Error initializing sources: {str(e)}")
            return 0


def check_source(source):
    """Check a source for new articles and projects"""
    global progress
    
    start_time = time.time()
    
    # Create a log entry
    try:
        log_entry = ScrapeLog()
        log_entry.source_id = source.id
        log_entry.timestamp = datetime.datetime.utcnow()
        log_entry.status = "Started"
        log_entry.message = f"Starting scrape of {source.name} ({source.url})"
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        logger.error(f"Error creating log entry: {str(e)}")
        # Continue even if we can't create a log entry
        log_entry = None
    
    try:
        logger.info(f"Checking source: {source.name} ({source.url})")
        
        # Update source status
        source.last_checked = datetime.datetime.utcnow()
        source.status = "Checking"
        db.session.commit()
        
        # Fetch news links with timeout protection
        try:
            article_links = fetch_news_from_source(source.url)
            logger.info(f"Found {len(article_links)} potential article links at {source.url}")
        except Exception as e:
            logger.error(f"Error fetching links from {source.url}: {str(e)}")
            article_links = []
        
        # Update log if it exists
        if log_entry:
            log_entry.message = f"Found {len(article_links)} potential articles"
            log_entry.articles_found = len(article_links)
            db.session.commit()
        
        projects_added = 0
        processed_count = 0
        
        # Limit number of articles to check per source to prevent timeouts
        max_articles_per_source = 10
        if len(article_links) > max_articles_per_source:
            logger.info(f"Limiting to {max_articles_per_source} articles for source {source.name}")
            article_links = article_links[:max_articles_per_source]
        
        for article_url in article_links:
            try:
                # Check if already processed
                existing_article = NewsArticle.query.filter_by(url=article_url).first()
                if existing_article and existing_article.is_processed:
                    continue
                
                # Extract content with error handling
                try:
                    content = extract_article_content(article_url)
                except Exception as e:
                    logger.error(f"Error extracting content from {article_url}: {str(e)}")
                    continue
                
                if not content or not content.get('text'):
                    continue
                
                # Store article if new
                if not existing_article:
                    try:
                        # Create new article with separate attribute assignment
                        new_article = NewsArticle()
                        new_article.url = article_url
                        new_article.title = content.get('title', 'Untitled')
                        # Limit text size for database
                        new_article.content = content.get('text', '')[:65535]
                        new_article.published_date = content.get('publish_date')
                        new_article.source_id = source.id
                        new_article.created_at = datetime.datetime.utcnow()
                        
                        db.session.add(new_article)
                        db.session.commit()
                        existing_article = new_article
                    except Exception as e:
                        # Handle duplicate URL or other database errors
                        logger.error(f"Error adding article {article_url}: {str(e)}")
                        db.session.rollback()
                        # Try to get the article again after rollback
                        existing_article = NewsArticle.query.filter_by(url=article_url).first()
                        if not existing_article:
                            # Skip this article if we can't add or retrieve it
                            continue
                
                # Try to extract project data
                try:
                    project_data = extract_project_data(article_url, content)
                except Exception as e:
                    logger.error(f"Error extracting project data from {article_url}: {str(e)}")
                    project_data = None
                
                if project_data:
                    # Check if project already exists with similar name and company
                    try:
                        # Handle both traditional and new enhanced format keys
                        project_name = project_data.get('Name', project_data.get('name', ''))
                        project_company = project_data.get('Company', project_data.get('company', ''))
                        
                        logger.info(f"Checking for existing project: {project_name} by {project_company}")
                        
                        existing_projects = Project.query.filter(
                            Project.name.ilike(f"%{project_name}%"),
                            Project.company.ilike(f"%{project_company}%")
                        ).all()
                    except Exception as e:
                        logger.error(f"Error querying existing projects: {str(e)}")
                        existing_projects = []
                    
                    if not existing_projects:
                        try:
                            # Calculate the next index
                            max_index = db.session.query(db.func.max(Project.index)).scalar() or 0
                            next_index = max_index + 1
                            
                            # Format dates
                            if isinstance(project_data.get("Announcement Date"), str):
                                try:
                                    announcement_date = datetime.datetime.strptime(
                                        project_data["Announcement Date"], "%d-%m-%Y"
                                    ).date()
                                except ValueError:
                                    announcement_date = datetime.datetime.now().date()
                            else:
                                announcement_date = datetime.datetime.now().date()
                            
                            # Create new project with separate attribute assignment
                            new_project = Project()
                            new_project.index = next_index
                            new_project.type = project_data["Type"]
                            new_project.name = project_data["Name"]
                            new_project.company = project_data["Company"]
                            new_project.ownership = project_data["Ownership"]
                            new_project.pli_status = project_data["PLI/Non-PLI"]
                            new_project.state = project_data["State"]
                            new_project.location = project_data["Location"]
                            new_project.announcement_date = announcement_date
                            new_project.category = project_data["Category"]
                            new_project.input_type = project_data["Input"]
                            new_project.output_type = project_data["Output"]
                            new_project.cell_capacity = project_data.get("Cell Capacity", 0)
                            new_project.module_capacity = project_data.get("Module Capacity", 0)
                            new_project.integration_capacity = project_data.get("Integration Capacity", 0)
                            new_project.status = project_data["Status"]
                            new_project.land_acquisition = project_data["Land Acquisition"]
                            new_project.power_approval = project_data["Power Approval"]
                            new_project.environment_clearance = project_data["Environment Clearance"]
                            new_project.almm_listing = project_data["ALMM Listing"]
                            new_project.investment_usd = project_data.get("Investment USD", 0)
                            new_project.investment_inr = project_data.get("Investment INR", 0)
                            new_project.expected_completion = project_data["Expected Completion"]
                            new_project.last_updated = datetime.datetime.now().date()
                            new_project.source = article_url
                            
                            db.session.add(new_project)
                            db.session.commit()
                            projects_added += 1
                            progress.add_projects(1)  # Update the progress tracker
                            logger.info(f"Added new project: {new_project.name} from {article_url}")
                        except Exception as e:
                            logger.error(f"Error adding project from {article_url}: {str(e)}")
                            db.session.rollback()
                
                # Mark article as processed
                try:
                    if existing_article:
                        existing_article.is_processed = True
                        db.session.commit()
                        processed_count += 1
                except Exception as e:
                    logger.error(f"Error marking article as processed: {str(e)}")
                    db.session.rollback()
            
            except Exception as article_error:
                logger.error(f"Error processing article {article_url}: {str(article_error)}")
                # Continue to next article
        
        # Update source status
        source.status = "Success"
        db.session.commit()
        
        # Update log
        if log_entry:
            log_entry.status = "Completed"
            log_entry.message = f"Processed {processed_count} articles, added {projects_added} projects"
            log_entry.projects_added = projects_added
            db.session.commit()
        
        logger.info(f"Completed checking {source.name}. Processed: {processed_count}, Projects added: {projects_added}")
        
        # Return the number of projects added from this source
        return projects_added
        
    except Exception as e:
        # Update source status on error
        try:
            source.status = "Error"
            db.session.commit()
        except:
            pass
        
        # Update log
        if log_entry:
            try:
                log_entry.status = "Error"
                log_entry.message = f"Error checking source: {str(e)}"
                db.session.commit()
            except:
                pass
        
        logger.error(f"Error checking source {source.name}: {str(e)}")
        return 0  # No projects added when there's an error
    
    finally:
        # Log execution time
        execution_time = time.time() - start_time
        logger.info(f"Source check for {source.name} completed in {execution_time:.2f} seconds")


def check_all_sources():
    """Check all sources for new articles and projects"""
    global progress
    
    initialize_sources()  # Make sure we have sources to check
    
    logger.info("Starting check of all sources")
    
    # Get all sources
    sources = Source.query.all()
    
    if not sources:
        logger.warning("No sources found in database")
        progress.complete()
        return
    
    # Reset progress tracker
    progress.reset()
    
    # Process each source
    for source in sources:
        check_source(source)
        progress.increment_source()  # Update progress tracker
        time.sleep(5)  # Small delay between sources to avoid overloading
    
    # Mark as completed
    progress.complete()
    logger.info("Completed check of all sources")


def run_manual_check():
    """Run a manual check of all sources (for API endpoint)"""
    # Reset the progress tracker
    progress.reset()
    
    # Run the check in a separate thread to prevent blocking
    thread = threading.Thread(target=_run_check_thread)
    thread.daemon = True
    thread.start()
    
    return {"status": "success", "message": "Check started in background"}
    
def _run_check_thread():
    """Background thread to run the check process"""
    
    # Reset the progress counter before starting
    progress.reset()
    
    try:
        logger.info("Starting manual check of all sources in background thread")
        
        # Create a new application context for the entire thread
        ctx = app.app_context()
        ctx.push()
        
        try:
            # First make sure all sources are properly initialized
            # This ensures new sources are added to the database
            initialize_sources()
            logger.info("Sources initialized, beginning source check")
            
            # Get all sources first and ensure they're sorted
            # to maintain consistent order of processing
            sources = Source.query.order_by(Source.name).all()
            total_sources = len(sources)
            
            # Update progress tracker with total sources
            progress.total_sources = total_sources
            logger.info(f"Found {total_sources} sources to check")
            
            # Track the actual processed sources to ensure accurate reporting
            actual_processed = 0
            
            # Set timeout limits
            max_source_time_per_source = 120  # seconds per source (increased)
            max_total_time = 3600  # 60 minutes total max (increased)
            consecutive_error_count = 0
            max_consecutive_errors = 5  # Stop after 5 consecutive errors
            
            # Process each source
            for i, source in enumerate(sources):
                source_start = time.time()
                
                try:
                    logger.info(f"Processing source {i+1}/{total_sources}: {source.name}")
                    
                    # Process source directly with proper error handling
                    # No additional app context needed
                    try:
                        # Process the source and get project count
                        projects_added = check_source(source)
                        actual_processed += 1
                        
                        # Reset error count on success
                        if projects_added >= 0:  # 0 is valid (no projects found)
                            consecutive_error_count = 0
                        
                    except Exception as source_error:
                        logger.error(f"Error checking source {source.name}: {str(source_error)}")
                        consecutive_error_count += 1
                                
                except Exception as e:
                    logger.error(f"Error processing source {source.name}: {str(e)}")
                    consecutive_error_count += 1
                
                # Always increment the counter, even if there was an error
                progress.processed_sources = actual_processed
                
                # Add a small delay between sources 
                elapsed = time.time() - source_start
                if elapsed < 2 and i < total_sources - 1:  # Don't delay after the last source
                    time.sleep(2)  # Small fixed delay
                
                # Stop if we've been running too long
                if progress.get_state()['elapsed'] > max_total_time:
                    logger.warning(f"Stopping source check due to time limit ({max_total_time/60:.1f} minutes)")
                    break
                    
                # Stop if too many consecutive errors (possible connectivity issue)
                if consecutive_error_count >= max_consecutive_errors:
                    logger.warning(f"Stopping source check due to {consecutive_error_count} consecutive errors")
                    break
            
            logger.info(f"Completed checking all sources. Processed {actual_processed} of {total_sources}.")
        
        except Exception as e:
            logger.error(f"Error in source processing: {str(e)}")
            progress.set_error(str(e))
        
        finally:
            # Pop the application context when done
            ctx.pop()
            
    except Exception as e:
        logger.error(f"Error in manual check thread: {str(e)}")
        progress.set_error(str(e))
        
    finally:
        # Always mark as completed to prevent hanging UI
        progress.complete()
