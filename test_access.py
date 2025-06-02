"""
Simple test for accessing news sources to identify 403 or other access issues
"""

import requests
import logging
from bs4 import BeautifulSoup
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# List of sources to test
TEST_SOURCES = [
    "https://www.thehindu.com/sci-tech/energy-and-environment/",
    "https://energy.economictimes.indiatimes.com/tag/solar+projects",
    "https://www.saurenergy.com/solar-energy-news",
    "https://renewablewatch.in/category/solar/"
]

# List of articles to test
TEST_ARTICLES = [
    "https://www.thehindu.com/sci-tech/energy-and-environment/history-future-value-india-rooftop-solar-programme-explained/article68335798.ece",
    "https://energy.economictimes.indiatimes.com/news/renewable/tata-power-secures-350-mw-solar-project-from-sjvn-in-rajasthan/108303329",
    "https://www.saurenergy.com/solar-energy-news/central-electronics-unveils-tender-for-1-mw-solar-plant-in-ghaziabad",
    "https://renewablewatch.in/2023/03/15/statkraft-enters-into-5-gw-solar-power-ppa-with-greenstat-india/"
]

def test_source_access(url):
    """Test if a source can be accessed"""
    logger.info(f"Testing access to source: {url}")
    
    try:
        # Set headers to make our request look like a normal browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        logger.info(f"Status code: {response.status_code}")
        if response.status_code == 200:
            logger.info("Access successful")
            
            # Check if we can parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.text if soup.title else "No title found"
            logger.info(f"Page title: {title}")
            
            # Log the number of links found
            links = soup.find_all('a', href=True)
            logger.info(f"Found {len(links)} links on the page")
            
            return True
        elif response.status_code == 403:
            logger.error("Access forbidden (403) - Website is likely blocking scraping")
            return False
        else:
            logger.warning(f"Access unsuccessful with status code {response.status_code}")
            return False
    
    except Exception as e:
        logger.error(f"Error accessing {url}: {e}")
        return False

def test_article_access(url):
    """Test if an article can be accessed"""
    logger.info(f"Testing access to article: {url}")
    
    try:
        # Set headers to make our request look like a normal browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        logger.info(f"Status code: {response.status_code}")
        if response.status_code == 200:
            logger.info("Access successful")
            
            # Check if we can parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.text if soup.title else "No title found"
            logger.info(f"Article title: {title}")
            
            # Try to extract some content
            content_elements = soup.find_all(['p', 'article', 'div', 'section'])
            content_sample = content_elements[0].text[:100] if content_elements else "No content found"
            logger.info(f"Content sample: {content_sample}...")
            
            return True
        elif response.status_code == 403:
            logger.error("Access forbidden (403) - Website is likely blocking scraping")
            return False
        else:
            logger.warning(f"Access unsuccessful with status code {response.status_code}")
            return False
    
    except Exception as e:
        logger.error(f"Error accessing {url}: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting direct test of source and article access")
    
    # Test sources
    logger.info("Testing access to source websites...")
    source_success = 0
    for idx, source_url in enumerate(TEST_SOURCES):
        logger.info(f"Testing source {idx+1}/{len(TEST_SOURCES)}: {source_url}")
        if test_source_access(source_url):
            source_success += 1
        logger.info("-" * 80)
        time.sleep(1)  # Add delay to avoid being blocked
    
    logger.info(f"Source access test complete. Successfully accessed {source_success}/{len(TEST_SOURCES)} sources.")
    
    # Test articles
    logger.info("Testing access to specific articles...")
    article_success = 0
    for idx, article_url in enumerate(TEST_ARTICLES):
        logger.info(f"Testing article {idx+1}/{len(TEST_ARTICLES)}: {article_url}")
        if test_article_access(article_url):
            article_success += 1
        logger.info("-" * 80)
        time.sleep(1)  # Add delay to avoid being blocked
    
    logger.info(f"Article access test complete. Successfully accessed {article_success}/{len(TEST_ARTICLES)} articles.")