"""
Test the automatic project detection with real article URLs
This script tests the fixed content extraction and project data mapping
"""

import logging
import sys
import enhanced_scraper
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])

# Test URLs to check (recent active articles)
TEST_URLS = [
    "https://energy.economictimes.indiatimes.com/news/renewable/india-one-of-the-most-exciting-growth-markets-for-clean-energy-globally-gcl/101053249",
    "https://www.saurenergy.com/solar-energy-news/rajasthan-solar-park-with-8550-mw-capacity-to-be-set-up",
    "https://energy.economictimes.indiatimes.com/news/renewable/adani-green-energy-signs-ppa-for-1-7-gw-solar-power-project-with-seci/100998266"
]

def test_extraction_and_mapping(url):
    """Test if content extraction and project data mapping works correctly"""
    print(f"\n\n{'='*80}\nTesting URL: {url}\n{'='*80}")
    
    try:
        # Extract content
        print("1. Testing content extraction...")
        content_dict = enhanced_scraper.extract_article_content(url)
        
        if not content_dict:
            print("FAILED: Content extraction returned None")
            return
            
        print(f"SUCCESS: Content extracted as expected")
        print(f"Title: {content_dict.get('title')}")
        print(f"Content length: {len(content_dict.get('text', ''))}")
        print(f"Keys returned: {list(content_dict.keys())}")
        
        # Extract project data
        print("\n2. Testing project data extraction...")
        project_data = enhanced_scraper.extract_project_data(url, content_dict)
        
        if not project_data:
            print("FAILED: Project data extraction returned None")
            return
            
        print("SUCCESS: Project data extracted as expected")
        
        # Check if both formats are present (lowercase and capitalized keys)
        lowercase_keys = [k for k in project_data.keys() if k.islower() or k.startswith('_')]
        uppercase_keys = [k for k in project_data.keys() if k[0].isupper()]
        
        print(f"Lowercase keys count: {len(lowercase_keys)}")
        print(f"Uppercase keys count: {len(uppercase_keys)}")
        
        if len(lowercase_keys) > 0 and len(uppercase_keys) > 0:
            print("SUCCESS: Both lowercase and uppercase keys are present")
        else:
            print("WARNING: Only one key format is present")
            
        # Print the extracted project data
        print("\nExtracted Project Data:")
        print(f"Type: {project_data.get('Type', project_data.get('type', 'N/A'))}")
        print(f"Name: {project_data.get('Name', project_data.get('name', 'N/A'))}")
        print(f"Company: {project_data.get('Company', project_data.get('company', 'N/A'))}")
        print(f"Location: {project_data.get('Location', project_data.get('location', 'N/A'))}")
        print(f"State: {project_data.get('State', project_data.get('state', 'N/A'))}")
        print(f"Generation Capacity: {project_data.get('Generation Capacity', project_data.get('generation_capacity', 'N/A'))}")
        print(f"Storage Capacity: {project_data.get('Storage Capacity', project_data.get('storage_capacity', 'N/A'))}")
        print(f"Investment USD: {project_data.get('Investment USD', project_data.get('investment_usd', 'N/A'))}")
        print(f"Investment INR: {project_data.get('Investment INR', project_data.get('investment_inr', 'N/A'))}")
        print(f"Expected Completion: {project_data.get('Expected Completion', project_data.get('expected_completion', 'N/A'))}")
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    print(f"Testing automatic project detection with enhanced_scraper")
    print(f"Current time: {datetime.now()}")
    
    # Test each URL
    for url in TEST_URLS:
        test_extraction_and_mapping(url)
        print("\n")

if __name__ == "__main__":
    main()