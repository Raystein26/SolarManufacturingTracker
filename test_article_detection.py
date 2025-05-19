"""
Direct test of article detection with specific URLs
"""

import logging
import enhanced_scraper
from app import app, db
from models import Project
import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# List of test articles that should be about solar projects in India
TEST_ARTICLES = [
    "https://www.thehindu.com/sci-tech/energy-and-environment/history-future-value-india-rooftop-solar-programme-explained/article68335798.ece",
    "https://energy.economictimes.indiatimes.com/news/renewable/tata-power-secures-350-mw-solar-project-from-sjvn-in-rajasthan/108303329",
    "https://www.saurenergy.com/solar-energy-news/central-electronics-unveils-tender-for-1-mw-solar-plant-in-ghaziabad",
    "https://renewablewatch.in/2023/03/15/statkraft-enters-into-5-gw-solar-power-ppa-with-greenstat-india/"
]

def test_article_detection(url):
    """Test if an article can be detected as a project"""
    logger.info(f"Testing article: {url}")
    
    try:
        # Extract content
        logger.info("Extracting content...")
        content = enhanced_scraper.extract_article_content(url)
        
        if not content or not content.get('text'):
            logger.warning(f"Failed to extract content from {url}")
            logger.debug(f"Content response: {content}")
            return False
        
        logger.info(f"Successfully extracted content from {url}")
        logger.info(f"Title: {content.get('title', 'No title')}")
        content_preview = content.get('text', '')[:200]
        logger.info(f"Content preview: {content_preview}...")
        
        # Check if it's about an Indian project
        india_score = enhanced_scraper.is_india_project(content.get('text', ''))
        logger.info(f"India score: {india_score}")
        
        # Check project type scores
        project_type_scores = enhanced_scraper.determine_project_type(content.get('text', ''))
        logger.info(f"Project type scores: {project_type_scores}")
        
        # Find the most likely project type
        max_score = 0
        project_type = None
        
        for type_name, score in project_type_scores.items():
            if score > max_score:
                max_score = score
                project_type = type_name
        
        logger.info(f"Most likely project type: {project_type} with score {max_score}")
        
        # Check pipeline score
        pipeline_score = enhanced_scraper.is_pipeline_project(content.get('text', ''))
        logger.info(f"Pipeline score: {pipeline_score}")
        
        # Use the full extraction function
        project_data = enhanced_scraper.extract_project_data(url, content)
        
        if project_data:
            logger.info(f"Project detected successfully! Project data: {project_data}")
            return True
        else:
            logger.warning("No project detected from this article")
            return False
    
    except Exception as e:
        logger.error(f"Error processing article {url}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def simulate_adding_project(url):
    """Simulate adding a project to the database (for testing)"""
    with app.app_context():
        test_title = f"Test Solar Project - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        try:
            # Find max index
            max_index = db.session.query(db.func.max(Project.index)).scalar() or 0
            
            # Create a simple test project
            new_project = Project()
            new_project.index = max_index + 1
            new_project.type = "Solar"
            new_project.name = test_title
            new_project.company = "Test Company"
            new_project.state = "Test State"
            new_project.location = "Test Location"
            new_project.announcement_date = datetime.datetime.now().date()
            new_project.category = "Generation"
            new_project.status = "Announced"
            new_project.source = url
            new_project.last_updated = datetime.datetime.now().date()
            new_project.created_at = datetime.datetime.now()
            
            db.session.add(new_project)
            db.session.commit()
            
            logger.info(f"Successfully added test project: {test_title}")
            return True
        except Exception as e:
            logger.error(f"Error adding test project: {e}")
            import traceback
            logger.error(traceback.format_exc())
            db.session.rollback()
            return False

if __name__ == "__main__":
    logger.info("Starting direct test of article detection")
    
    # First, test if we can add a project to the database
    logger.info("Testing database project addition...")
    add_success = simulate_adding_project("https://test.com/test-article")
    
    if add_success:
        logger.info("Database connection and project addition works properly!")
    else:
        logger.error("Failed to add test project to database - issue with database connection")
    
    # Test each article
    successes = 0
    for idx, article_url in enumerate(TEST_ARTICLES):
        logger.info(f"Testing article {idx+1}/{len(TEST_ARTICLES)}: {article_url}")
        if test_article_detection(article_url):
            successes += 1
        logger.info("-" * 80)
    
    logger.info(f"Test complete. Successfully detected {successes}/{len(TEST_ARTICLES)} projects.")