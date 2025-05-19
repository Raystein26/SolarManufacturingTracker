"""
Test the entire scraper pipeline with a sample article
"""

import logging
import enhanced_scraper
from app import app, db
from models import Project, Source, NewsArticle
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test content for a solar project in India
TEST_CONTENT = """
Premier Energies Partners with Sino-American for Solar Module Plant in Hyderabad

Premier Energies, India's second-largest integrated solar cell and module manufacturer, has announced a strategic partnership with Sino-American Silicon Products Inc., a global leader in renewable energy, to establish a state-of-the-art solar module manufacturing facility in Hyderabad.

The new facility will have a 2 GW production capacity for TOPCon modules, aligning with India's push for self-reliance in renewable energy manufacturing.

This partnership brings together Premier Energies' manufacturing expertise and Sino-American's technological capabilities, strengthening India's position in the global solar supply chain.

According to company officials, the plant will be operational by the first quarter of 2024 and create over 700 jobs in Hyderabad.

The initial investment for the facility is estimated at Rs 1,200 crore (approximately $150 million).
"""

def test_add_to_database():
    """Test if a project can be extracted and added to the database"""
    url = "https://test-article-url/premier-energies-solar-module-plant"
    title = "Premier Energies Partners with Sino-American for Solar Module Plant in Hyderabad"
    
    # Create a sample NewsArticle
    print(f"Creating sample NewsArticle...")
    with app.app_context():
        # Check if article already exists
        existing_article = NewsArticle.query.filter_by(url=url).first()
        if existing_article:
            print(f"Article already exists, using existing one")
            article = existing_article
        else:
            # Create a test source if needed
            source = Source.query.filter_by(name="Test Source").first()
            if not source:
                source = Source(url="https://test-source.com", name="Test Source", 
                               description="Test source for pipeline testing")
                db.session.add(source)
                db.session.commit()
                print(f"Created test source: {source.name}")
            
            # Create the article
            article = NewsArticle(
                url=url,
                title=title,
                content=TEST_CONTENT,
                source_id=source.id,
                is_processed=False,
                created_at=datetime.utcnow()
            )
            db.session.add(article)
            db.session.commit()
            print(f"Created test article: {article.title}")
    
    # Extract project data
    print(f"\nExtracting project data...")
    project_data = enhanced_scraper.extract_project_data(url, TEST_CONTENT)
    
    if not project_data:
        print(f"Failed to extract project data")
        return False
        
    print(f"Successfully extracted project data:")
    print(f"Type: {project_data.get('Type', project_data.get('type'))}")
    print(f"Name: {project_data.get('Name', project_data.get('name'))}")
    print(f"Capacity: {project_data.get('Generation Capacity', project_data.get('generation_capacity'))} GW")
    
    # Create a project in the database
    print(f"\nCreating project in database...")
    with app.app_context():
        # Check if project already exists
        existing_project = Project.query.filter_by(
            name=project_data.get('Name', project_data.get('name')),
            source=url
        ).first()
        
        if existing_project:
            print(f"Project already exists: {existing_project.name}")
            return True
            
        # Create a new project
        project = Project()
        
        # Map data to project fields - this logic should match project_tracker.py
        for key, value in project_data.items():
            if hasattr(project, key) and value is not None:
                setattr(project, key, value)
        
        # Ensure required fields are set
        project.created_at = datetime.utcnow()
        project.last_updated = datetime.utcnow()
        project.source = url
        
        # Add to database
        db.session.add(project)
        db.session.commit()
        print(f"Created new project: {project.name}")
        
        # Verify project was added
        added_project = Project.query.filter_by(source=url).first()
        if added_project:
            print(f"Success: Project successfully added to database")
            print(f"Project ID: {added_project.id}")
            print(f"Project Type: {added_project.type}")
            print(f"Project Name: {added_project.name}")
            print(f"Generation Capacity: {added_project.generation_capacity} GW")
            return True
        else:
            print(f"Error: Project was not found in database after adding")
            return False

if __name__ == "__main__":
    success = test_add_to_database()
    if success:
        print("\nTest Passed: Project data extraction and database addition is working properly")
    else:
        print("\nTest Failed: Issues with project data extraction or database addition")