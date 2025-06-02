"""
Test script to fetch and process articles from specific sources
"""

import logging
import time
import enhanced_scraper
from app import app, db
from models import Project, Source
import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_articles_from_source(source_url, limit=5):
    """
    Fetch and check articles from a specific source
    Args:
        source_url: URL of the source to check
        limit: Maximum number of articles to check
    """
    logger.info(f"Checking articles from source: {source_url}")
    
    try:
        # Find the source in the database
        with app.app_context():
            source = Source.query.filter(Source.url.like(f"%{source_url}%")).first()
            if source:
                logger.info(f"Found source in database: {source.name}")
            else:
                logger.warning(f"Source not found in database: {source_url}")
        
        # Get articles from the source
        logger.info("Fetching articles...")
        article_urls = enhanced_scraper.fetch_news_from_source(source_url)
        
        if not article_urls:
            logger.warning(f"No articles found from source: {source_url}")
            return 0
        
        logger.info(f"Found {len(article_urls)} articles")
        
        # Limit the number of articles to check
        articles_to_check = article_urls[:limit]
        logger.info(f"Will check the first {len(articles_to_check)} articles")
        
        projects_found = 0
        
        # Process each article
        for i, article_url in enumerate(articles_to_check):
            logger.info(f"Checking article {i+1}/{len(articles_to_check)}: {article_url}")
            
            try:
                # Extract project data
                project_data = enhanced_scraper.extract_project_data(article_url)
                
                if project_data:
                    logger.info(f"Found a valid project: {project_data.get('name', 'Unnamed')}")
                    logger.info(f"Project type: {project_data.get('type', 'Unknown')}")
                    logger.info(f"Project capacity: {project_data.get('capacity', 'Unknown')}")
                    projects_found += 1
                else:
                    logger.info("No project data found in this article")
                
            except Exception as e:
                logger.error(f"Error processing article: {e}")
            
            # Add a delay to avoid overwhelming the server
            time.sleep(1)
        
        logger.info(f"Found {projects_found} projects in {len(articles_to_check)} articles")
        return projects_found
    
    except Exception as e:
        logger.error(f"Error checking articles from source: {e}")
        return 0

def check_single_article(article_url):
    """Check a single article directly"""
    logger.info(f"Checking single article: {article_url}")
    
    try:
        # Extract content
        content = enhanced_scraper.extract_article_content(article_url)
        
        if not content or not content.get('text'):
            logger.warning(f"Failed to extract content from {article_url}")
            return False
        
        logger.info(f"Successfully extracted content")
        logger.info(f"Title: {content.get('title', 'No title')}")
        content_preview = content.get('text', '')[:200]
        logger.info(f"Content preview: {content_preview}...")
        
        # Check if it's about an Indian project
        india_score = enhanced_scraper.is_india_project(content.get('text', ''))
        logger.info(f"India score: {india_score}")
        
        # Check pipeline score
        pipeline_score = enhanced_scraper.is_pipeline_project(content.get('text', ''))
        logger.info(f"Pipeline score: {pipeline_score}")
        
        # Check project type scores
        project_type_scores = enhanced_scraper.determine_project_type(content.get('text', ''))
        logger.info(f"Project type scores: {project_type_scores}")
        
        # Use the full extraction function
        project_data = enhanced_scraper.extract_project_data(article_url, content)
        
        if project_data:
            logger.info(f"Project detected successfully!")
            logger.info(f"Project details:")
            for key, value in project_data.items():
                logger.info(f"  {key}: {value}")
            
            # Manually add to database
            with app.app_context():
                # Check if we already have this project by checking the source URL
                existing = Project.query.filter_by(source=article_url).first()
                if existing:
                    logger.info(f"This project is already in the database (ID: {existing.id})")
                    return False
                
                # Find max index
                max_index = db.session.query(db.func.max(Project.index)).scalar() or 0
                
                # Create a new project
                new_project = Project()
                new_project.index = max_index + 1
                new_project.type = project_data.get('type', 'Solar')
                new_project.name = project_data.get('name', 'Unnamed Project')
                new_project.company = project_data.get('company', '')
                new_project.state = project_data.get('state', '')
                new_project.location = project_data.get('location', '')
                new_project.announcement_date = datetime.datetime.now().date()
                new_project.category = project_data.get('category', 'Generation')
                
                # Set appropriate capacity fields based on type
                if project_data.get('type') == 'Solar':
                    new_project.generation_capacity = project_data.get('capacity')
                elif project_data.get('type') == 'Battery':
                    new_project.storage_capacity = project_data.get('capacity')
                elif project_data.get('type') == 'Wind':
                    new_project.generation_capacity = project_data.get('capacity')
                elif project_data.get('type') == 'Hydro':
                    new_project.generation_capacity = project_data.get('capacity')
                elif project_data.get('type') == 'Green Hydrogen':
                    new_project.hydrogen_production = project_data.get('capacity')
                elif project_data.get('type') == 'Biofuel':
                    new_project.biofuel_capacity = project_data.get('capacity')
                
                new_project.status = 'Announced'
                new_project.source = article_url
                new_project.last_updated = datetime.datetime.now().date()
                
                if project_data.get('investment_usd'):
                    new_project.investment_usd = project_data.get('investment_usd')
                
                if project_data.get('expected_completion'):
                    new_project.expected_completion = project_data.get('expected_completion')
                
                # Save to database
                db.session.add(new_project)
                db.session.commit()
                
                logger.info(f"Added new project to database with ID: {new_project.id}")
                return True
            
        else:
            logger.info("No project detected in this article")
            return False
    
    except Exception as e:
        logger.error(f"Error checking article: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("Starting article checker")
    
    # Check some working articles directly
    successful_articles = [
        "https://www.thehindu.com/sci-tech/energy-and-environment/history-future-value-india-rooftop-solar-programme-explained/article68335798.ece"
    ]
    
    for article in successful_articles:
        logger.info("=" * 80)
        logger.info(f"Testing known working article: {article}")
        result = check_single_article(article)
        logger.info("=" * 80)
    
    # Check specific sources
    test_sources = [
        "https://www.thehindu.com/sci-tech/energy-and-environment/",
        "https://energy.economictimes.indiatimes.com/tag/solar+projects",
        "https://www.saurenergy.com/solar-energy-news"
    ]
    
    for source in test_sources:
        logger.info("=" * 80)
        logger.info(f"Testing source: {source}")
        check_articles_from_source(source, limit=3)
        logger.info("=" * 80)