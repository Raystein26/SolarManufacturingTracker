"""
Add test solar projects directly to the database
This script adds sample projects based on real articles to test the system
"""

import logging
import datetime
from app import app, db
from models import Project

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_test_project(
    project_type,
    name,
    company,
    state,
    location,
    capacity,
    source_url
):
    """Add a test project directly to the database"""
    logger.info(f"Adding test {project_type} project: {name}")
    
    with app.app_context():
        # Check if we already have this project
        existing = Project.query.filter_by(source=source_url).first()
        if existing:
            logger.info(f"This project is already in the database (ID: {existing.id})")
            return False
        
        # Find max index
        max_index = db.session.query(db.func.max(Project.index)).scalar() or 0
        
        # Create a new project
        new_project = Project()
        new_project.index = max_index + 1
        new_project.type = project_type
        new_project.name = name
        new_project.company = company
        new_project.state = state
        new_project.location = location
        new_project.announcement_date = datetime.datetime.now().date()
        new_project.category = "Generation" if project_type in ["Solar", "Wind", "Hydro"] else "Storage"
        
        # Set appropriate capacity fields based on type
        if project_type == "Solar":
            new_project.generation_capacity = capacity
        elif project_type == "Battery":
            new_project.storage_capacity = capacity
        elif project_type == "Wind":
            new_project.generation_capacity = capacity
        elif project_type == "Hydro":
            new_project.generation_capacity = capacity
        elif project_type == "Green Hydrogen":
            new_project.hydrogen_production = capacity
        elif project_type == "Biofuel":
            new_project.biofuel_capacity = capacity
        
        new_project.status = 'Announced'
        new_project.source = source_url
        new_project.last_updated = datetime.datetime.now().date()
        
        # Save to database
        db.session.add(new_project)
        db.session.commit()
        
        logger.info(f"Added new {project_type} project to database with ID: {new_project.id}")
        return True

if __name__ == "__main__":
    logger.info("Adding test solar projects to the database")
    
    # List of test projects based on real announcements
    test_projects = [
        {
            "type": "Solar",
            "name": "350 MW Solar Project in Rajasthan",
            "company": "Tata Power Solar",
            "state": "Rajasthan",
            "location": "Jodhpur",
            "capacity": 0.35,  # GW
            "source": "https://energy.economictimes.indiatimes.com/news/renewable/tata-power-secures-350-mw-solar-project-from-sjvn-in-rajasthan/108303329"
        },
        {
            "type": "Solar",
            "name": "Rooftop Solar Programme in Kerala",
            "company": "Kerala State Electricity Board",
            "state": "Kerala", 
            "location": "Statewide",
            "capacity": 0.2,  # GW
            "source": "https://www.thehindu.com/sci-tech/energy-and-environment/history-future-value-india-rooftop-solar-programme-explained/article68335798.ece"
        },
        {
            "type": "Solar",
            "name": "1 MW Solar Plant in Ghaziabad",
            "company": "Central Electronics Limited",
            "state": "Uttar Pradesh",
            "location": "Ghaziabad",
            "capacity": 0.001,  # GW (1 MW)
            "source": "https://www.saurenergy.com/solar-energy-news/central-electronics-unveils-tender-for-1-mw-solar-plant-in-ghaziabad"
        },
        {
            "type": "Solar",
            "name": "5 GW Solar Power PPA with Greenstat India",
            "company": "Statkraft",
            "state": "Multiple States",
            "location": "Various",
            "capacity": 5.0,  # GW
            "source": "https://renewablewatch.in/2023/03/15/statkraft-enters-into-5-gw-solar-power-ppa-with-greenstat-india/"
        }
    ]
    
    # Add each test project
    added = 0
    for project in test_projects:
        success = add_test_project(
            project["type"],
            project["name"],
            project["company"],
            project["state"],
            project["location"],
            project["capacity"],
            project["source"]
        )
        if success:
            added += 1
    
    logger.info(f"Successfully added {added}/{len(test_projects)} test projects")