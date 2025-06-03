#!/usr/bin/env python3
"""
Test script to debug scraper functionality and identify where projects are being filtered out
"""

import sys
import os
sys.path.append('.')

from scraper import (
    is_india_project, 
    is_renewable_project, 
    is_pipeline_project,
    extract_project_data
)

# Test cases with real article content that should pass
test_cases = [
    {
        "name": "Solar Manufacturing Project",
        "content": """
        Adani Green Energy announced plans to build a 5 GW solar manufacturing facility in Gujarat. 
        The project will require an investment of Rs 15,000 crore and is expected to be completed by 2026.
        The solar plant will manufacture solar modules and cells for the Indian market.
        """,
        "should_detect": True,
        "expected_type": "Solar"
    },
    {
        "name": "Battery Storage Project",
        "content": """
        Reliance Industries will set up a 2 GWh lithium-ion battery manufacturing plant in Maharashtra.
        The energy storage facility will be commissioned by 2025 with an investment of $500 million.
        The battery factory will produce cells for electric vehicles and grid storage applications.
        """,
        "should_detect": True,
        "expected_type": "Battery"
    },
    {
        "name": "Wind Energy Project",
        "content": """
        Suzlon Energy announced a 1.5 GW wind farm project in Rajasthan.
        The wind power plant will be developed with an investment of Rs 8,000 crore.
        Construction is expected to begin in 2025 and complete by 2027.
        """,
        "should_detect": True,
        "expected_type": "Wind"
    },
    {
        "name": "Hydrogen Production Project", 
        "content": """
        NTPC plans to establish a 100 MW electrolyzer facility for green hydrogen production in Andhra Pradesh.
        The hydrogen plant will produce clean fuel for industrial applications.
        The project involves an investment of Rs 2,000 crore and will be operational by 2026.
        """,
        "should_detect": True,
        "expected_type": "Green Hydrogen"
    },
    {
        "name": "Non-renewable Project",
        "content": """
        Coal India Limited reported strong quarterly results with increased production.
        The company's thermal power generation rose by 15% compared to last year.
        No new investments in renewable energy were announced.
        """,
        "should_detect": False,
        "expected_type": None
    },
    {
        "name": "Foreign Project",
        "content": """
        Tesla announced a 3 GW solar panel factory in Nevada, USA.
        The gigafactory will produce solar cells and battery storage systems.
        Construction will begin in 2025 with a $2 billion investment.
        """,
        "should_detect": False,
        "expected_type": None
    },
    {
        "name": "Completed Project",
        "content": """
        Adani Solar has inaugurated its 2 GW solar manufacturing facility in Gujarat.
        The plant was commissioned last month and has started operations.
        The facility is already operational and producing solar modules.
        """,
        "should_detect": False,
        "expected_type": None
    }
]

def test_individual_functions():
    """Test each filtering function individually"""
    print("=== TESTING INDIVIDUAL FUNCTIONS ===\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test Case {i}: {test_case['name']}")
        print("-" * 50)
        
        content = test_case['content']
        
        # Test India detection
        is_india = is_india_project(content)
        print(f"India Project: {is_india}")
        
        # Test renewable detection
        is_renewable, project_type = is_renewable_project(content)
        print(f"Renewable Project: {is_renewable}, Type: {project_type}")
        
        # Test pipeline detection
        is_pipeline = is_pipeline_project(content)
        print(f"Pipeline Project: {is_pipeline}")
        
        # Overall result
        should_pass = is_india and is_renewable and is_pipeline
        expected = test_case['should_detect']
        
        status = "✓ PASS" if should_pass == expected else "✗ FAIL"
        print(f"Expected: {expected}, Got: {should_pass} - {status}")
        
        if should_pass != expected:
            print(f"  Issue: India={is_india}, Renewable={is_renewable}, Pipeline={is_pipeline}")
        
        print()

def test_full_extraction():
    """Test full project data extraction"""
    print("=== TESTING FULL EXTRACTION ===\n")
    
    for i, test_case in enumerate(test_cases, 1):
        if not test_case['should_detect']:
            continue
            
        print(f"Test Case {i}: {test_case['name']}")
        print("-" * 50)
        
        # Create mock content structure
        mock_content = {
            'title': test_case['name'],
            'text': test_case['content'],
            'publish_date': None
        }
        
        # Test extraction
        project_data = extract_project_data("https://test.com/article", mock_content)
        
        if project_data:
            print("✓ Project extracted successfully!")
            print(f"  Type: {project_data.get('type')}")
            print(f"  Name: {project_data.get('name')}")
            print(f"  Company: {project_data.get('company')}")
            print(f"  Location: {project_data.get('location')}")
            print(f"  Investment: {project_data.get('investment_usd')}")
            
            # Check capacity fields
            capacity_fields = ['generation_capacity', 'storage_capacity', 'electrolyzer_capacity', 'biofuel_capacity']
            for field in capacity_fields:
                if project_data.get(field):
                    print(f"  {field}: {project_data[field]}")
        else:
            print("✗ No project data extracted")
        
        print()

def test_with_real_keywords():
    """Test with content that contains actual renewable energy keywords"""
    print("=== TESTING WITH REAL KEYWORDS ===\n")
    
    # Test with minimal renewable content
    minimal_renewable = "Solar project announced in India with 100 MW capacity"
    print("Minimal renewable content test:")
    print(f"Content: {minimal_renewable}")
    
    is_india = is_india_project(minimal_renewable)
    is_renewable, project_type = is_renewable_project(minimal_renewable)
    is_pipeline = is_pipeline_project(minimal_renewable)
    
    print(f"India: {is_india}, Renewable: {is_renewable} ({project_type}), Pipeline: {is_pipeline}")
    
    if is_india and is_renewable and is_pipeline:
        print("✓ Should be detected as valid project")
    else:
        print("✗ Failed basic detection")
    
    print()

if __name__ == "__main__":
    print("SCRAPER DEBUG TEST SUITE")
    print("=" * 60)
    print()
    
    test_individual_functions()
    test_full_extraction()
    test_with_real_keywords()
    
    print("Test completed. Check results above to identify filtering issues.")