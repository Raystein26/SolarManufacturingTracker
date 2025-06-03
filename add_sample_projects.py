#!/usr/bin/env python3
"""
Add sample renewable energy projects for demonstration purposes
"""

import sys
import os
sys.path.append('.')

from app import app, db
from models import Project
from datetime import datetime, date

def add_sample_projects():
    """Add sample renewable energy projects to the database"""
    
    sample_projects = [
        {
            "index": 1,
            "type": "Solar",
            "name": "Adani Green Energy 5 GW Solar Manufacturing Facility",
            "company": "Adani Green Energy",
            "ownership": "Private",
            "pli_status": "PLI",
            "state": "Gujarat",
            "location": "Mundra, Gujarat",
            "announcement_date": date(2025, 3, 15),
            "category": "Manufacturing",
            "input_type": "Silicon Wafers",
            "output_type": "Solar Modules",
            "generation_capacity": 5.0,
            "status": "Pipeline",
            "land_acquisition": "Completed",
            "power_approval": "In Progress",
            "environment_clearance": "Approved",
            "almm_listing": "Applied",
            "investment_usd": 2000.0,
            "expected_completion": "2026",
            "source": "https://www.adanigreenenergy.com/newsroom/press-releases"
        },
        {
            "index": 2,
            "type": "Battery",
            "name": "Reliance 2 GWh Lithium-ion Battery Manufacturing Plant",
            "company": "Reliance Industries",
            "ownership": "Private",
            "pli_status": "PLI",
            "state": "Maharashtra",
            "location": "Jamnagar, Gujarat",
            "announcement_date": date(2025, 2, 28),
            "category": "Manufacturing",
            "input_type": "Lithium Materials",
            "output_type": "Battery Cells",
            "storage_capacity": 2.0,
            "status": "Pipeline",
            "land_acquisition": "Completed",
            "power_approval": "Approved",
            "environment_clearance": "In Progress",
            "almm_listing": "N/A",
            "investment_usd": 1500.0,
            "expected_completion": "2025",
            "source": "https://www.ril.com/newsroom"
        },
        {
            "index": 3,
            "type": "Wind",
            "name": "Suzlon 1.5 GW Wind Farm Project",
            "company": "Suzlon Energy",
            "ownership": "Private",
            "pli_status": "Non-PLI",
            "state": "Rajasthan",
            "location": "Jaisalmer, Rajasthan",
            "announcement_date": date(2025, 4, 10),
            "category": "Generation",
            "input_type": "Wind",
            "output_type": "Electricity",
            "generation_capacity": 1.5,
            "status": "Pipeline",
            "land_acquisition": "In Progress",
            "power_approval": "Applied",
            "environment_clearance": "Pending",
            "almm_listing": "N/A",
            "investment_usd": 1200.0,
            "expected_completion": "2027",
            "source": "https://www.suzlon.com/media/press-releases"
        },
        {
            "index": 4,
            "type": "Green Hydrogen",
            "name": "NTPC 100 MW Green Hydrogen Production Facility",
            "company": "NTPC Limited",
            "ownership": "Public",
            "pli_status": "Non-PLI",
            "state": "Andhra Pradesh",
            "location": "Visakhapatnam, Andhra Pradesh",
            "announcement_date": date(2025, 1, 20),
            "category": "Production",
            "input_type": "Renewable Electricity",
            "output_type": "Green Hydrogen",
            "electrolyzer_capacity": 100.0,
            "status": "Pipeline",
            "land_acquisition": "Completed",
            "power_approval": "Approved",
            "environment_clearance": "Approved",
            "almm_listing": "N/A",
            "investment_usd": 800.0,
            "expected_completion": "2026",
            "source": "https://www.ntpc.co.in/media/press-releases"
        },
        {
            "index": 5,
            "type": "Solar",
            "name": "Tata Solar 3 GW Manufacturing Hub",
            "company": "Tata Power Solar",
            "ownership": "Private",
            "pli_status": "PLI",
            "state": "Tamil Nadu",
            "location": "Chennai, Tamil Nadu",
            "announcement_date": date(2025, 5, 5),
            "category": "Manufacturing",
            "input_type": "Silicon Wafers",
            "output_type": "Solar Cells and Modules",
            "generation_capacity": 3.0,
            "status": "Pipeline",
            "land_acquisition": "In Progress",
            "power_approval": "Applied",
            "environment_clearance": "Applied",
            "almm_listing": "Applied",
            "investment_usd": 1800.0,
            "expected_completion": "2026",
            "source": "https://www.tatapower.com/media/press-releases"
        },
        {
            "index": 6,
            "type": "Biofuel",
            "name": "Indian Oil Corporation 500 Million Litres Ethanol Plant",
            "company": "Indian Oil Corporation",
            "ownership": "Public",
            "pli_status": "Non-PLI",
            "state": "Uttar Pradesh",
            "location": "Gorakhpur, Uttar Pradesh",
            "announcement_date": date(2025, 3, 1),
            "category": "Production",
            "input_type": "Sugarcane",
            "output_type": "Ethanol",
            "biofuel_capacity": 500.0,
            "status": "Pipeline",
            "land_acquisition": "Completed",
            "power_approval": "Approved",
            "environment_clearance": "In Progress",
            "almm_listing": "N/A",
            "investment_usd": 600.0,
            "expected_completion": "2025",
            "source": "https://iocl.com/media-centre/press-releases"
        }
    ]
    
    with app.app_context():
        # Check if projects already exist
        existing_count = Project.query.count()
        if existing_count > 0:
            print(f"Database already contains {existing_count} projects. Skipping sample data insertion.")
            return
        
        print("Adding sample renewable energy projects...")
        
        for project_data in sample_projects:
            # Create project with current timestamp
            project = Project()
            for key, value in project_data.items():
                setattr(project, key, value)
            
            project.last_updated = date.today()
            project.created_at = datetime.utcnow()
            project.updated_at = datetime.utcnow()
            
            db.session.add(project)
            print(f"Added: {project.name}")
        
        db.session.commit()
        print(f"Successfully added {len(sample_projects)} sample projects to the database.")

if __name__ == "__main__":
    add_sample_projects()