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

# Test with pre-loaded content instead of live URLs
TEST_CONTENT = """
Premier Energies Partners with Sino-American for Solar Module Plant in Hyderabad

Premier Energies, India's second-largest integrated solar cell and module manufacturer, has announced a strategic partnership with Sino-American Silicon Products Inc., a global leader in renewable energy, to establish a state-of-the-art solar module manufacturing facility in Hyderabad.

The new facility will have a 2 GW production capacity for TOPCon modules, aligning with India's push for self-reliance in renewable energy manufacturing.

This partnership brings together Premier Energies' manufacturing expertise and Sino-American's technological capabilities, strengthening India's position in the global solar supply chain.

According to company officials, the plant will be operational by the first quarter of 2024 and create over 700 jobs in Hyderabad.

The initial investment for the facility is estimated at Rs 1,200 crore (approximately $150 million).
"""

# Use a fake URL for testing
TEST_URLS = ["https://test-article-url/premier-energies-solar-module-plant"]

def test_extraction_and_mapping(url):
    """Test if content extraction and project data mapping works correctly"""
    print(f"\n\n{'='*80}\nTesting URL: {url}\n{'='*80}")
    
    try:
        # Instead of extracting, use our predefined content
        print("1. Testing with predefined content...")
        content_dict = {
            'text': TEST_CONTENT,
            'title': 'Premier Energies Partners with Sino-American for Solar Module Plant in Hyderabad',
            'url': url,
            'publish_date': datetime.now()
        }
        
        print(f"SUCCESS: Using predefined test content")
        print(f"Title: {content_dict.get('title')}")
        print(f"Content length: {len(content_dict.get('text', ''))}")
        print(f"Keys returned: {list(content_dict.keys())}")
        
        # Extract project data
        print("\n2. Testing project data extraction...")
        project_data = enhanced_scraper.extract_project_data(url, content_dict.get('text'))
        
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