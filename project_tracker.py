import os
import logging
import time
import datetime
from app import app, db
from models import Project, Source, NewsArticle, ScrapeLog
from scraper import fetch_news_from_source, extract_article_content, extract_project_data

logger = logging.getLogger(__name__)

# List of reputable sources for renewable energy projects in India
DEFAULT_SOURCES = [
    "https://mercomindia.com/",
    "https://www.pv-magazine-india.com/",
    "https://jmkresearch.com/",
    "https://www.pv-tech.org/",
    "https://energy.economictimes.indiatimes.com/",
    "https://www.business-standard.com/industry/news/power",
    "https://www.livemint.com/industry/energy"
]

def initialize_sources():
    """Initialize the database with default sources if empty"""
    source_count = Source.query.count()
    if source_count == 0:
        logger.info("No sources found in database. Initializing default sources.")
        for url in DEFAULT_SOURCES:
            # Extract domain name for the source name
            domain = url.split("//")[-1].split("/")[0]
            if domain.startswith('www.'):
                domain = domain[4:]
            name = ' '.join(word.capitalize() for word in domain.split('.')[0].split('-'))
            
            new_source = Source(
                url=url,
                name=name,
                description=f"News source for renewable energy projects in India: {url}",
                created_at=datetime.datetime.utcnow()
            )
            
            db.session.add(new_source)
        
        db.session.commit()
        logger.info(f"Added {len(DEFAULT_SOURCES)} default sources to the database.")


def check_source(source):
    """Check a source for new articles and projects"""
    start_time = time.time()
    
    # Create a log entry
    log_entry = ScrapeLog(
        source_id=source.id,
        timestamp=datetime.datetime.utcnow(),
        status="Started",
        message=f"Starting scrape of {source.name} ({source.url})"
    )
    db.session.add(log_entry)
    db.session.commit()
    
    try:
        logger.info(f"Checking source: {source.name} ({source.url})")
        
        # Update source status
        source.last_checked = datetime.datetime.utcnow()
        source.status = "Checking"
        db.session.commit()
        
        # Fetch news links
        article_links = fetch_news_from_source(source.url)
        logger.info(f"Found {len(article_links)} potential article links at {source.url}")
        
        # Update log
        log_entry.message = f"Found {len(article_links)} potential articles"
        log_entry.articles_found = len(article_links)
        db.session.commit()
        
        projects_added = 0
        processed_count = 0
        
        for article_url in article_links:
            # Check if already processed
            existing_article = NewsArticle.query.filter_by(url=article_url).first()
            if existing_article and existing_article.is_processed:
                continue
                
            # Extract content
            content = extract_article_content(article_url)
            
            if not content or not content['text']:
                continue
                
            # Store article if new
            if not existing_article:
                new_article = NewsArticle(
                    url=article_url,
                    title=content['title'],
                    content=content['text'][:65535],  # Limit text size for database
                    published_date=content['publish_date'],
                    source_id=source.id,
                    created_at=datetime.datetime.utcnow()
                )
                db.session.add(new_article)
                db.session.commit()
                existing_article = new_article
            
            # Try to extract project data
            project_data = extract_project_data(article_url, content)
            
            if project_data:
                # Check if project already exists with similar name and company
                existing_projects = Project.query.filter(
                    Project.name.ilike(f"%{project_data['Name']}%"),
                    Project.company.ilike(f"%{project_data['Company']}%")
                ).all()
                
                if not existing_projects:
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
                    
                    # Create new project
                    new_project = Project(
                        index=next_index,
                        type=project_data["Type"],
                        name=project_data["Name"],
                        company=project_data["Company"],
                        ownership=project_data["Ownership"],
                        pli_status=project_data["PLI/Non-PLI"],
                        state=project_data["State"],
                        location=project_data["Location"],
                        announcement_date=announcement_date,
                        category=project_data["Category"],
                        input_type=project_data["Input"],
                        output_type=project_data["Output"],
                        cell_capacity=project_data.get("Cell Capacity", 0),
                        module_capacity=project_data.get("Module Capacity", 0),
                        integration_capacity=project_data.get("Integration Capacity", 0),
                        status=project_data["Status"],
                        land_acquisition=project_data["Land Acquisition"],
                        power_approval=project_data["Power Approval"],
                        environment_clearance=project_data["Environment Clearance"],
                        almm_listing=project_data["ALMM Listing"],
                        investment_usd=project_data.get("Investment USD", 0),
                        investment_inr=project_data.get("Investment INR", 0),
                        expected_completion=project_data["Expected Completion"],
                        last_updated=datetime.datetime.now().date(),
                        source=article_url
                    )
                    
                    db.session.add(new_project)
                    db.session.commit()
                    projects_added += 1
                    logger.info(f"Added new project: {new_project.name} from {article_url}")
            
            # Mark article as processed
            existing_article.is_processed = True
            db.session.commit()
            processed_count += 1
        
        # Update source status
        source.status = "Success"
        db.session.commit()
        
        # Update log
        log_entry.status = "Completed"
        log_entry.message = f"Processed {processed_count} articles, added {projects_added} projects"
        log_entry.projects_added = projects_added
        db.session.commit()
        
        logger.info(f"Completed checking {source.name}. Processed: {processed_count}, Projects added: {projects_added}")
        
    except Exception as e:
        # Update source status on error
        source.status = "Error"
        db.session.commit()
        
        # Update log
        log_entry.status = "Error"
        log_entry.message = f"Error checking source: {str(e)}"
        db.session.commit()
        
        logger.error(f"Error checking source {source.name}: {str(e)}")
    
    finally:
        # Log execution time
        execution_time = time.time() - start_time
        logger.info(f"Source check for {source.name} completed in {execution_time:.2f} seconds")


def check_all_sources():
    """Check all sources for new articles and projects"""
    initialize_sources()  # Make sure we have sources to check
    
    logger.info("Starting check of all sources")
    
    # Get all sources
    sources = Source.query.all()
    
    if not sources:
        logger.warning("No sources found in database")
        return
    
    # Process each source
    for source in sources:
        check_source(source)
        time.sleep(5)  # Small delay between sources to avoid overloading
    
    logger.info("Completed check of all sources")


def run_manual_check():
    """Run a manual check of all sources (for API endpoint)"""
    try:
        logger.info("Starting manual check of all sources")
        with app.app_context():
            check_all_sources()
        return {"status": "success", "message": "Completed check of all sources"}
    except Exception as e:
        logger.error(f"Error in manual check: {str(e)}")
        return {"status": "error", "message": str(e)}
