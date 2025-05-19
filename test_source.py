"""
Test a single news source to verify it allows scraping
"""
import sys
import logging
from app import app, db
from models import Source
import enhanced_scraper
import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_source(url, name, description):
    """Add a source to the database if it doesn't exist"""
    with app.app_context():
        # Check if already exists
        existing = Source.query.filter_by(url=url).first()
        if existing:
            logger.info(f"Source already exists: {name} ({url})")
            return existing
        
        # Create new source
        source = Source()
        source.url = url
        source.name = name
        source.description = description
        source.status = "New"
        source.created_at = datetime.datetime.utcnow()
        
        db.session.add(source)
        db.session.commit()
        
        logger.info(f"Added new source: {name} ({url})")
        return source

def test_source(url):
    """Test if a source allows web scraping"""
    logger.info(f"Testing source: {url}")
    
    try:
        # Try to fetch article links
        article_links = enhanced_scraper.fetch_news_from_source(url)
        
        if not article_links:
            logger.warning(f"No article links found at {url}")
            return False, 0
        
        logger.info(f"Found {len(article_links)} article links")
        
        # Try to fetch content of the first article
        if len(article_links) > 0:
            test_article = article_links[0]
            logger.info(f"Testing article: {test_article}")
            
            content = enhanced_scraper.extract_article_content(test_article)
            
            if not content or not content.get('text'):
                logger.warning(f"No content extracted from {test_article}")
                return False, len(article_links)
            
            logger.info(f"Successfully extracted content from {test_article}")
            logger.info(f"Title: {content.get('title', 'No title')}")
            logger.info(f"Content preview: {content.get('text', '')[:200]}...")
            
            return True, len(article_links)
        
        return True, len(article_links)
    
    except Exception as e:
        logger.error(f"Error testing source {url}: {e}")
        return False, 0

if __name__ == "__main__":
    # Sources to test
    sources_to_test = [
        (
            "https://renewablewatch.in/category/solar/",
            "Renewable Watch Solar",
            "Renewable Watch is a leading magazine covering the Indian renewable power sector."
        ),
        (
            "https://energy.economictimes.indiatimes.com/tag/solar+projects",
            "ET Energy Solar Projects",
            "Economic Times Energy section focusing on solar projects in India."
        ),
        (
            "https://www.thehindu.com/sci-tech/energy-and-environment/",
            "The Hindu Energy",
            "The Hindu's coverage of energy and environment news in India."
        ),
        (
            "https://www.saurenergy.com/solar-energy-news",
            "Saur Energy Solar",
            "Saur Energy International is a media platform dedicated to renewable energy."
        ),
        (
            "https://timesofindia.indiatimes.com/topic/renewable-energy",
            "Times of India Renewable",
            "Times of India's coverage of renewable energy news."
        )
    ]
    
    successful_sources = []
    
    # If a specific URL is provided, test only that one
    if len(sys.argv) > 1:
        url = sys.argv[1]
        success, article_count = test_source(url)
        
        if success:
            logger.info(f"Source {url} allows web scraping. Found {article_count} articles.")
            
            # Add to database if it passes the test
            if input("Add this source to the database? (y/n): ").lower() == 'y':
                add_source(url, url, "Added through test script")
        else:
            logger.warning(f"Source {url} does not allow web scraping or no articles found.")
    else:
        # Test all sources
        for url, name, description in sources_to_test:
            success, article_count = test_source(url)
            
            if success:
                logger.info(f"SUCCESS: {name} ({url}) allows web scraping. Found {article_count} articles.")
                successful_sources.append((url, name, description))
            else:
                logger.warning(f"FAILED: {name} ({url}) does not allow web scraping or no articles found.")
        
        # Add all successful sources
        logger.info(f"Adding {len(successful_sources)} successful sources to database")
        for url, name, description in successful_sources:
            add_source(url, name, description)