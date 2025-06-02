"""
Direct test of article detection and database addition
"""

import logging
import enhanced_scraper
from app import app, db
from models import Project, Source
import datetime
import re
import trafilatura

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_article_direct(url):
    """Extract article content directly using trafilatura"""
    logger.info(f"Extracting content from {url}")
    try:
        # Download the webpage
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            logger.error(f"Failed to download content from {url}")
            return None
        
        # Extract the content
        content = trafilatura.extract(downloaded, 
                                      include_comments=False, 
                                      include_tables=True,
                                      favor_precision=True)
        
        if not content:
            logger.error(f"No content extracted from {url}")
            return None
        
        # Get title from URL as a fallback
        title = url.split('/')[-1].replace('-', ' ').title()
        
        # Try to get a better title from the HTML if possible
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(downloaded, 'html.parser')
            if soup.title:
                title = soup.title.string
        except Exception as e:
            logger.warning(f"Error extracting title: {e}")
        
        logger.info(f"Extracted content with length: {len(content)}")
        logger.info(f"Title: {title}")
        
        return {
            'text': content,
            'title': title,
            'url': url
        }
    except Exception as e:
        logger.error(f"Error extracting content: {e}")
        return None

def manually_add_solar_project(url, title, content, capacity=None, company=None, location=None):
    """Manually add a solar project to the database with extracted content"""
    logger.info(f"Manually adding solar project from {url}")
    
    with app.app_context():
        # Check if we already have this project
        existing = Project.query.filter_by(source=url).first()
        if existing:
            logger.info(f"This project is already in the database (ID: {existing.id})")
            return False
        
        # Find max index
        max_index = db.session.query(db.func.max(Project.index)).scalar() or 0
        
        # Extract capacity if not provided
        if not capacity:
            # Try to extract capacity from the content
            capacity_patterns = [
                r'(\d+(?:\.\d+)?)\s*(?:GW|MW|MWac|MWp|GWac|GWp)',
                r'(\d+(?:\.\d+)?)\s*(?:gigawatt|megawatt)s?',
                r'capacity\s+of\s+(\d+(?:\.\d+)?)\s*(?:GW|MW|MWac|MWp|GWac|GWp)',
                r'(\d+(?:\.\d+)?)\s*(?:GW|MW|MWac|MWp|GWac|GWp)\s+(?:solar|pv|photovoltaic)'
            ]
            
            for pattern in capacity_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    capacity = float(match.group(1))
                    # Convert to GW if in MW
                    if 'MW' in match.group(0) or 'megawatt' in match.group(0).lower():
                        capacity = capacity / 1000
                    logger.info(f"Extracted capacity: {capacity} GW")
                    break
        
        # Extract company if not provided
        if not company:
            # Try to extract company from the content
            company_patterns = [
                r'(?:company|developer|firm|corporation)\s+([A-Z][A-Za-z\s]+?)(?:Ltd\.?|Inc\.?|Limited|Corporation)?[\s,\.]',
                r'([A-Z][A-Za-z\s]+?)(?:Ltd\.?|Inc\.?|Limited|Corporation)[\s,\.]',
                r'([A-Z][A-Za-z\s]+?)\s+(?:has|have|is|are|will|plans to)',
                r'([A-Z][A-Za-z\s]+?)\s+(?:awarded|won|secured|signed)'
            ]
            
            for pattern in company_patterns:
                match = re.search(pattern, content)
                if match:
                    company = match.group(1).strip()
                    if len(company) > 5 and len(company) < 50:  # Reasonable company name length
                        logger.info(f"Extracted company: {company}")
                        break
        
        # Extract location if not provided
        if not location:
            # Try to extract location from the content
            location_patterns = [
                r'in\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)*),\s+(?:India|state)',
                r'in\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\s+(?:district|region|state)',
                r'(?:located|situated|based)\s+in\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)'
            ]
            
            for pattern in location_patterns:
                match = re.search(pattern, content)
                if match:
                    location = match.group(1).strip()
                    logger.info(f"Extracted location: {location}")
                    break
        
        # Create a new project
        new_project = Project()
        new_project.index = max_index + 1
        new_project.type = "Solar"  # We're focusing on solar projects
        new_project.name = title[:200] if title else "Solar Project"
        
        if company:
            new_project.company = company[:200]
        
        if location:
            india_states = [
                "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", 
                "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", 
                "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", 
                "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", 
                "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal"
            ]
            
            # Try to identify state
            for state in india_states:
                if state.lower() in content.lower() or state.lower() in location.lower():
                    new_project.state = state
                    break
            
            new_project.location = location[:100]
        
        new_project.announcement_date = datetime.datetime.now().date()
        new_project.category = "Generation"
        
        if capacity:
            new_project.generation_capacity = capacity
        
        new_project.status = 'Announced'
        new_project.source = url
        new_project.last_updated = datetime.datetime.now().date()
        
        # Save to database
        db.session.add(new_project)
        db.session.commit()
        
        logger.info(f"Added new solar project to database with ID: {new_project.id}")
        return True

# Test with a specific project article
def test_with_article(url):
    """Test with a specific article URL"""
    logger.info(f"Testing with article: {url}")
    
    # Extract content
    article_data = extract_article_direct(url)
    
    if not article_data:
        logger.error("Failed to extract article content")
        return False
    
    content = article_data['text']
    title = article_data['title']
    
    # Print a preview of the content
    logger.info(f"Content preview: {content[:200]}...")
    
    # Check if it's about a solar project in India
    solar_terms = ['solar', 'pv', 'photovoltaic', 'renewable', 'clean energy']
    india_terms = ['india', 'indian', 'bharat', 'gujarat', 'rajasthan', 'tamil nadu', 'karnataka']
    project_terms = ['mw', 'gw', 'megawatt', 'gigawatt', 'capacity', 'project', 'plant', 'installation']
    
    solar_score = sum(1 for term in solar_terms if term.lower() in content.lower()) / len(solar_terms)
    india_score = sum(1 for term in india_terms if term.lower() in content.lower()) / len(india_terms)
    project_score = sum(1 for term in project_terms if term.lower() in content.lower()) / len(project_terms)
    
    combined_score = (solar_score + india_score + project_score) / 3
    
    logger.info(f"Solar score: {solar_score}")
    logger.info(f"India score: {india_score}")
    logger.info(f"Project score: {project_score}")
    logger.info(f"Combined score: {combined_score}")
    
    if combined_score > 0.3:  # Lower threshold to catch more potential projects
        logger.info("Article likely describes a solar project in India")
        
        # Try to add it to the database
        result = manually_add_solar_project(url, title, content)
        return result
    else:
        logger.info("Article likely not about a solar project in India")
        return False

if __name__ == "__main__":
    # Test articles that are likely to be about solar projects in India
    test_articles = [
        "https://www.thehindu.com/sci-tech/energy-and-environment/history-future-value-india-rooftop-solar-programme-explained/article68335798.ece",
        "https://www.thehindu.com/sci-tech/energy-and-environment/indian-solar-module-costs-fall-by-40-in-2023-become-cheapest-globally-report/article67821243.ece",
        "https://www.thehindu.com/business/Economy/india-to-add-25-gw-solar-capacity-in-2024-says-report/article67783003.ece"
    ]
    
    successes = 0
    for article in test_articles:
        logger.info("=" * 80)
        if test_with_article(article):
            successes += 1
        logger.info("=" * 80)
    
    logger.info(f"Successfully added {successes}/{len(test_articles)} solar projects")