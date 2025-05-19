"""
Test script to fetch and process articles from specific sources
"""
import sys
import logging
import enhanced_scraper
from enhanced_scraper import extract_article_content, extract_project_data

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
        # Fetch articles
        article_links = enhanced_scraper.fetch_news_from_source(source_url)
        logger.info(f"Found {len(article_links)} articles")
        
        if limit:
            article_links = article_links[:limit]
            logger.info(f"Limiting to {limit} articles")
        
        for i, article_url in enumerate(article_links):
            logger.info(f"Processing article {i+1}/{len(article_links)}: {article_url}")
            
            try:
                # Extract content
                content = extract_article_content(article_url)
                
                if not content or not content.get('text'):
                    logger.warning(f"No content extracted from {article_url}")
                    continue
                
                logger.info(f"Article title: {content.get('title', 'No title')}")
                logger.info(f"Content sample: {content.get('text', '')[:200]}...")
                
                # First check if it's about India using our criteria
                india_score = enhanced_scraper.is_india_project(content.get('text', ''))
                logger.info(f"India score: {india_score}")
                
                # Check project type scores
                project_type_scores = enhanced_scraper.determine_project_type(content.get('text', ''))
                logger.info(f"Project type scores: {project_type_scores}")
                
                # Get most likely project type
                max_score = 0
                project_type = None
                for type_name, score in project_type_scores.items():
                    if score > max_score:
                        max_score = score
                        project_type = type_name
                
                logger.info(f"Most likely project type: {project_type} (score: {max_score})")
                
                # Check pipeline score
                pipeline_score = enhanced_scraper.is_pipeline_project(content.get('text', ''))
                logger.info(f"Pipeline score: {pipeline_score}")
                
                # Test full extraction
                project_data = extract_project_data(article_url, content)
                
                if project_data:
                    logger.info(f"PROJECT DETECTED: {project_data}")
                else:
                    logger.info("No project detected")
                
                logger.info("-------------------------------------------")
                
            except Exception as e:
                logger.error(f"Error processing article {article_url}: {e}")
    
    except Exception as e:
        logger.error(f"Error checking source {source_url}: {e}")

def check_single_article(article_url):
    """Check a single article directly"""
    logger.info(f"Checking single article: {article_url}")
    
    try:
        # Extract content
        content = extract_article_content(article_url)
        
        if not content or not content.get('text'):
            logger.warning(f"No content extracted from {article_url}")
            return
        
        logger.info(f"Article title: {content.get('title', 'No title')}")
        logger.info(f"Content sample: {content.get('text', '')[:200]}...")
        
        # First check if it's about India using our criteria
        india_score = enhanced_scraper.is_india_project(content.get('text', ''))
        logger.info(f"India score: {india_score}")
        
        # Check project type scores
        project_type_scores = enhanced_scraper.determine_project_type(content.get('text', ''))
        logger.info(f"Project type scores: {project_type_scores}")
        
        # Get most likely project type
        max_score = 0
        project_type = None
        for type_name, score in project_type_scores.items():
            if score > max_score:
                max_score = score
                project_type = type_name
        
        logger.info(f"Most likely project type: {project_type} (score: {max_score})")
        
        # Check pipeline score
        pipeline_score = enhanced_scraper.is_pipeline_project(content.get('text', ''))
        logger.info(f"Pipeline score: {pipeline_score}")
        
        # Test full extraction
        project_data = extract_project_data(article_url, content)
        
        if project_data:
            logger.info(f"PROJECT DETECTED: {project_data}")
        else:
            logger.info("No project detected")
    
    except Exception as e:
        logger.error(f"Error processing article {article_url}: {e}")

if __name__ == "__main__":
    # Default sources to check
    sources = [
        "https://mercomindia.com/category/solar/",
        "https://pv-magazine-india.com/category/markets-policy/"
    ]
    
    # Direct article URLs for testing
    sample_articles = [
        "https://mercomindia.com/hero-future-energies-acquires-430-mw-solar-projects/",
        "https://pv-magazine-india.com/2025/05/16/jsr-commissions-16-mw-floating-solar-plant-in-telangana/",
        "https://mercomindia.com/premier-energies-partners-with-sino-american-for-solar-wafer-manufacturing/"
    ]
    
    if len(sys.argv) > 1:
        # Check if it's a full URL to a single article
        if "http" in sys.argv[1] and not "/category/" in sys.argv[1]:
            check_single_article(sys.argv[1])
        else:
            # Otherwise process as a source
            check_articles_from_source(sys.argv[1])
    else:
        # Check individual sample articles first
        for article in sample_articles:
            check_single_article(article)
            logger.info("-------------------------------------------")