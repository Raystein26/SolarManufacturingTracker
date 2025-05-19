"""
Add new news sources for renewable energy in India
"""
import sys
import logging
from app import app, db
from models import Source
import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_new_source(url, name, description):
    """
    Add a new news source to the database
    
    Args:
        url: Source URL
        name: Source name
        description: Source description
    
    Returns:
        True if added successfully, False otherwise
    """
    try:
        # Check if source already exists
        existing = Source.query.filter_by(url=url).first()
        if existing:
            logger.info(f"Source {name} already exists with URL {url}")
            return False
        
        # Create new source
        source = Source()
        source.url = url
        source.name = name
        source.description = description
        source.last_checked = None
        source.status = "New"
        source.created_at = datetime.datetime.utcnow()
        
        # Add to database
        db.session.add(source)
        db.session.commit()
        
        logger.info(f"Added new source: {name} ({url})")
        return True
    
    except Exception as e:
        logger.error(f"Error adding source {name}: {e}")
        db.session.rollback()
        return False

def add_multiple_sources(sources_list):
    """
    Add multiple sources from a list
    
    Args:
        sources_list: List of (url, name, description) tuples
    
    Returns:
        Number of sources added
    """
    count = 0
    for url, name, description in sources_list:
        if add_new_source(url, name, description):
            count += 1
    
    return count

if __name__ == "__main__":
    # New sources focused on renewable energy in India
    new_sources = [
        (
            "https://renewablewatch.in/category/solar/",
            "Renewable Watch Solar",
            "Renewable Watch is a leading magazine covering the Indian renewable power sector."
        ),
        (
            "https://power.economictimes.indiatimes.com/tag/solar+power",
            "ET Power Solar",
            "Economic Times Power section focusing on solar power in India."
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
            "https://www.energetica-india.net/news/india",
            "Energetica India",
            "Energetica India covers renewable energy news across the Indian subcontinent."
        ),
        (
            "https://www.saurenergy.com/solar-energy-news",
            "Saur Energy Solar",
            "Saur Energy International is a media platform dedicated to renewable energy, with focus on solar, wind and storage."
        ),
        (
            "https://www.business-standard.com/topic/solar-energy",
            "Business Standard Solar",
            "Business Standard's coverage of solar energy news in India."
        ),
        (
            "https://timesofindia.indiatimes.com/topic/renewable-energy",
            "Times of India Renewable",
            "Times of India's coverage of renewable energy news."
        ),
        (
            "https://www.indiainfoline.com/search/news/renewable-energy",
            "India Infoline Renewable",
            "India Infoline's coverage of renewable energy news."
        ),
        (
            "https://energy-utilities.com/news-category-India",
            "Energy Utilities India",
            "Energy Utilities' coverage of energy news in India."
        )
    ]
    
    with app.app_context():
        added = add_multiple_sources(new_sources)
        logger.info(f"Added {added} new sources out of {len(new_sources)}")
        
        # List all sources
        sources = Source.query.all()
        logger.info(f"Total sources: {len(sources)}")