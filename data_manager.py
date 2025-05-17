import os
import pandas as pd
import logging
import datetime
from app import db
from models import Project, Source, NewsArticle, ScrapeLog
from data_processor import clean_project_name

logger = logging.getLogger(__name__)

# Excel file constants
EXCEL_FILE = "india_renewable_projects.xlsx"
SOLAR_SHEET = "Solar Projects"
BATTERY_SHEET = "Battery Projects"
SOURCES_SHEET = "Sources"

def export_to_excel():
    """Export database to Excel file"""
    try:
        logger.info(f"Exporting database to {EXCEL_FILE}")
        
        # Get all projects
        solar_projects = Project.query.filter_by(type='Solar').all()
        battery_projects = Project.query.filter_by(type='Battery').all()
        
        # Get all sources
        sources = Source.query.all()
        
        # Create dataframes
        solar_df = pd.DataFrame([
            {
                'Index': p.index,
                'Type': p.type,
                'Name': clean_project_name(p.name),
                'Company': p.company,
                'Ownership': p.ownership,
                'PLI/Non-PLI': p.pli_status,
                'State': p.state,
                'Location': p.location,
                'Announcement Date': p.announcement_date.strftime('%d-%m-%Y') if p.announcement_date else 'NA',
                'Category': p.category if p.category else 'NA',
                'Input': p.input_type if p.input_type else 'NA',
                'Output': p.output_type if p.output_type else 'NA',
                'Cell Capacity (GW)': p.cell_capacity if p.cell_capacity is not None else 0.0,
                'Module Capacity (GW)': p.module_capacity if p.module_capacity is not None else 0.0,
                'Integration Capacity (GW)': p.integration_capacity if p.integration_capacity is not None else 0.0,
                'Status': p.status if p.status else 'NA',
                'Land Acquisition': p.land_acquisition if p.land_acquisition else 'NA',
                'Power Approval': p.power_approval if p.power_approval else 'NA',
                'Environment Clearance': p.environment_clearance if p.environment_clearance else 'NA',
                'ALMM Listing': p.almm_listing if p.almm_listing else 'NA',
                'Investment (USD Million)': p.investment_usd if p.investment_usd is not None else 0.0,
                'Investment (INR Billion)': p.investment_inr if p.investment_inr is not None else 0.0,
                'Expected Completion': p.expected_completion if p.expected_completion else 'NA',
                'Last Updated': p.last_updated.strftime('%d-%m-%Y') if p.last_updated else 'NA',
                'Source': p.source
            } 
            for p in solar_projects
        ])
        
        battery_df = pd.DataFrame([
            {
                'Index': p.index,
                'Type': p.type,
                'Name': clean_project_name(p.name),
                'Company': p.company,
                'Ownership': p.ownership,
                'PLI/Non-PLI': p.pli_status,
                'State': p.state,
                'Location': p.location,
                'Announcement Date': p.announcement_date.strftime('%d-%m-%Y') if p.announcement_date else 'NA',
                'Category': p.category if p.category else 'NA',
                'Input': p.input_type if p.input_type else 'NA',
                'Output': p.output_type if p.output_type else 'NA',
                'Cell Capacity (GWh)': p.cell_capacity if p.cell_capacity is not None else 0.0,
                'Module Capacity (GWh)': p.module_capacity if p.module_capacity is not None else 0.0,
                'Integration Capacity (GWh)': p.integration_capacity if p.integration_capacity is not None else 0.0,
                'Status': p.status if p.status else 'NA',
                'Land Acquisition': p.land_acquisition if p.land_acquisition else 'NA',
                'Power Approval': p.power_approval if p.power_approval else 'NA',
                'Environment Clearance': p.environment_clearance if p.environment_clearance else 'NA',
                'ALMM Listing': p.almm_listing if p.almm_listing else 'NA',
                'Investment (USD Million)': p.investment_usd if p.investment_usd is not None else 0.0,
                'Investment (INR Billion)': p.investment_inr if p.investment_inr is not None else 0.0,
                'Expected Completion': p.expected_completion if p.expected_completion else 'NA',
                'Last Updated': p.last_updated.strftime('%d-%m-%Y') if p.last_updated else 'NA',
                'Source': p.source
            } 
            for p in battery_projects
        ])
        
        sources_df = pd.DataFrame([
            {
                'Source URL': s.url,
                'Name': s.name,
                'Description': s.description,
                'Last Checked': s.last_checked.strftime('%Y-%m-%d %H:%M:%S') if s.last_checked else 'Never',
                'Status': s.status
            } 
            for s in sources
        ])
        
        # Create Excel writer
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"india_renewable_projects_{timestamp}.xlsx"
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            solar_df.to_excel(writer, sheet_name=SOLAR_SHEET, index=False)
            battery_df.to_excel(writer, sheet_name=BATTERY_SHEET, index=False)
            sources_df.to_excel(writer, sheet_name=SOURCES_SHEET, index=False)
            
        logger.info(f"Excel file created: {filename}")
        return filename
        
    except Exception as e:
        logger.error(f"Error exporting to Excel: {str(e)}")
        raise


def import_from_excel(excel_file):
    """Import data from Excel file"""
    try:
        logger.info(f"Importing data from {excel_file}")
        
        # Read Excel sheets
        solar_df = pd.read_excel(excel_file, sheet_name=SOLAR_SHEET)
        battery_df = pd.read_excel(excel_file, sheet_name=BATTERY_SHEET)
        sources_df = pd.read_excel(excel_file, sheet_name=SOURCES_SHEET)
        
        # Import sources
        sources_added = 0
        for _, row in sources_df.iterrows():
            url = row.get('Source URL')
            if not url or not isinstance(url, str):
                continue
                
            # Check if source exists
            existing_source = Source.query.filter_by(url=url).first()
            if not existing_source:
                new_source = Source(
                    url=url,
                    name=row.get('Name'),
                    description=row.get('Description'),
                    status=row.get('Status')
                )
                db.session.add(new_source)
                sources_added += 1
        
        db.session.commit()
        
        # Import solar projects
        solar_added = 0
        for _, row in solar_df.iterrows():
            name = row.get('Name')
            company = row.get('Company')
            
            if not name or not isinstance(name, str):
                continue
                
            # Check if project exists
            existing_project = Project.query.filter(
                Project.name.ilike(f"%{name}%"),
                Project.company.ilike(f"%{company}%") if company else True,
                Project.type == 'Solar'
            ).first()
            
            if not existing_project:
                # Parse dates
                try:
                    announcement_date = pd.to_datetime(row.get('Announcement Date')).date()
                except:
                    announcement_date = datetime.datetime.now().date()
                    
                try:
                    last_updated = pd.to_datetime(row.get('Last Updated')).date()
                except:
                    last_updated = datetime.datetime.now().date()
                
                new_project = Project(
                    index=row.get('Index'),
                    type='Solar',
                    name=name,
                    company=row.get('Company'),
                    ownership=row.get('Ownership'),
                    pli_status=row.get('PLI/Non-PLI'),
                    state=row.get('State'),
                    location=row.get('Location'),
                    announcement_date=announcement_date,
                    category=row.get('Category'),
                    input_type=row.get('Input'),
                    output_type=row.get('Output'),
                    cell_capacity=float(row.get('Cell Capacity (GW)', 0) or 0),
                    module_capacity=float(row.get('Module Capacity (GW)', 0) or 0),
                    integration_capacity=float(row.get('Integration Capacity (GW)', 0) or 0),
                    status=row.get('Status'),
                    land_acquisition=row.get('Land Acquisition'),
                    power_approval=row.get('Power Approval'),
                    environment_clearance=row.get('Environment Clearance'),
                    almm_listing=row.get('ALMM Listing'),
                    investment_usd=float(row.get('Investment (USD Million)', 0) or 0),
                    investment_inr=float(row.get('Investment (INR Billion)', 0) or 0),
                    expected_completion=row.get('Expected Completion'),
                    last_updated=last_updated,
                    source=row.get('Source')
                )
                db.session.add(new_project)
                solar_added += 1
        
        # Import battery projects
        battery_added = 0
        for _, row in battery_df.iterrows():
            name = row.get('Name')
            company = row.get('Company')
            
            if not name or not isinstance(name, str):
                continue
                
            # Check if project exists
            existing_project = Project.query.filter(
                Project.name.ilike(f"%{name}%"),
                Project.company.ilike(f"%{company}%") if company else True,
                Project.type == 'Battery'
            ).first()
            
            if not existing_project:
                # Parse dates
                try:
                    announcement_date = pd.to_datetime(row.get('Announcement Date')).date()
                except:
                    announcement_date = datetime.datetime.now().date()
                    
                try:
                    last_updated = pd.to_datetime(row.get('Last Updated')).date()
                except:
                    last_updated = datetime.datetime.now().date()
                
                new_project = Project(
                    index=row.get('Index'),
                    type='Battery',
                    name=name,
                    company=row.get('Company'),
                    ownership=row.get('Ownership'),
                    pli_status=row.get('PLI/Non-PLI'),
                    state=row.get('State'),
                    location=row.get('Location'),
                    announcement_date=announcement_date,
                    category=row.get('Category'),
                    input_type=row.get('Input'),
                    output_type=row.get('Output'),
                    cell_capacity=float(row.get('Cell Capacity (GWh)', 0) or 0),
                    module_capacity=float(row.get('Module Capacity (GWh)', 0) or 0),
                    integration_capacity=float(row.get('Integration Capacity (GWh)', 0) or 0),
                    status=row.get('Status'),
                    land_acquisition=row.get('Land Acquisition'),
                    power_approval=row.get('Power Approval'),
                    environment_clearance=row.get('Environment Clearance'),
                    almm_listing=row.get('ALMM Listing'),
                    investment_usd=float(row.get('Investment (USD Million)', 0) or 0),
                    investment_inr=float(row.get('Investment (INR Billion)', 0) or 0),
                    expected_completion=row.get('Expected Completion'),
                    last_updated=last_updated,
                    source=row.get('Source')
                )
                db.session.add(new_project)
                battery_added += 1
        
        db.session.commit()
        
        message = f"Import complete: Added {sources_added} sources, {solar_added} solar projects, and {battery_added} battery projects."
        logger.info(message)
        return message
        
    except Exception as e:
        logger.error(f"Error importing from Excel: {str(e)}")
        db.session.rollback()
        raise
