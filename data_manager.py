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

def export_to_excel():
    """Export database to Excel file with separate sheets for each renewable energy category"""
    try:
        logger.info(f"Exporting database to {EXCEL_FILE}")
        
        # Get projects by category
        solar_projects = Project.query.filter_by(type='Solar').all()
        battery_projects = Project.query.filter_by(type='Battery').all()
        wind_projects = Project.query.filter_by(type='Wind').all()
        hydro_projects = Project.query.filter_by(type='Hydro').all()
        hydrogen_projects = Project.query.filter(Project.type.in_(['Green Hydrogen', 'GreenHydrogen'])).all()
        biofuel_projects = Project.query.filter_by(type='Biofuel').all()
        
        # Get all sources
        sources = Source.query.all()
        
        # Helper function to create project dataframe
        def create_project_df(projects, project_type):
            return pd.DataFrame([
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
                    'Generation Capacity (GW)': p.generation_capacity if p.generation_capacity is not None else 0.0,
                    'Storage Capacity (GWh)': p.storage_capacity if p.storage_capacity is not None else 0.0,
                    'Cell Capacity (GW)': p.cell_capacity if p.cell_capacity is not None else 0.0,
                    'Module Capacity (GW)': p.module_capacity if p.module_capacity is not None else 0.0,
                    'Integration Capacity (GW)': p.integration_capacity if p.integration_capacity is not None else 0.0,
                    'Electrolyzer Capacity (MW)': p.electrolyzer_capacity if p.electrolyzer_capacity is not None else 0.0,
                    'Hydrogen Production (tons/day)': p.hydrogen_production if p.hydrogen_production is not None else 0.0,
                    'Biofuel Capacity (ML/year)': p.biofuel_capacity if p.biofuel_capacity is not None else 0.0,
                    'Feedstock Type': p.feedstock_type if p.feedstock_type else 'NA',
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
                for p in projects
            ])
        
        # Create dataframes for all renewable energy categories
        solar_df = create_project_df(solar_projects, 'Solar')
        battery_df = create_project_df(battery_projects, 'Battery') 
        wind_df = create_project_df(wind_projects, 'Wind')
        hydro_df = create_project_df(hydro_projects, 'Hydro')
        hydrogen_df = create_project_df(hydrogen_projects, 'Green Hydrogen')
        biofuel_df = create_project_df(biofuel_projects, 'Biofuel')
        
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
            # Create separate sheets for each renewable energy category
            if not solar_df.empty:
                solar_df.to_excel(writer, sheet_name='Solar Projects', index=False)
            if not battery_df.empty:
                battery_df.to_excel(writer, sheet_name='Battery Projects', index=False)
            if not wind_df.empty:
                wind_df.to_excel(writer, sheet_name='Wind Projects', index=False)
            if not hydro_df.empty:
                hydro_df.to_excel(writer, sheet_name='Hydro Projects', index=False)
            if not hydrogen_df.empty:
                hydrogen_df.to_excel(writer, sheet_name='Green Hydrogen Projects', index=False)
            if not biofuel_df.empty:
                biofuel_df.to_excel(writer, sheet_name='Biofuel Projects', index=False)
            
            # Add sources sheet
            sources_df.to_excel(writer, sheet_name='Sources', index=False)
            
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

def export_single_project_to_excel(project):
    """Export a single project to Excel file"""
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"project_{project.id}_{timestamp}.xlsx"
        
        # Create project data
        project_data = {
            'Index': project.index,
            'Type': project.type,
            'Name': clean_project_name(project.name),
            'Company': project.company,
            'Ownership': project.ownership,
            'PLI/Non-PLI': project.pli_status,
            'State': project.state,
            'Location': project.location,
            'Announcement Date': project.announcement_date.strftime('%d-%m-%Y') if project.announcement_date else 'NA',
            'Category': project.category if project.category else 'NA',
            'Input': project.input_type if project.input_type else 'NA',
            'Output': project.output_type if project.output_type else 'NA',
            'Generation Capacity (GW)': project.generation_capacity if project.generation_capacity is not None else 0.0,
            'Storage Capacity (GWh)': project.storage_capacity if project.storage_capacity is not None else 0.0,
            'Cell Capacity (GW)': project.cell_capacity if project.cell_capacity is not None else 0.0,
            'Module Capacity (GW)': project.module_capacity if project.module_capacity is not None else 0.0,
            'Integration Capacity (GW)': project.integration_capacity if project.integration_capacity is not None else 0.0,
            'Electrolyzer Capacity (MW)': project.electrolyzer_capacity if project.electrolyzer_capacity is not None else 0.0,
            'Hydrogen Production (tons/day)': project.hydrogen_production if project.hydrogen_production is not None else 0.0,
            'Biofuel Capacity (ML/year)': project.biofuel_capacity if project.biofuel_capacity is not None else 0.0,
            'Feedstock Type': project.feedstock_type if project.feedstock_type else 'NA',
            'Status': project.status,
            'Land Acquisition': project.land_acquisition if project.land_acquisition else 'NA',
            'Power Approval': project.power_approval if project.power_approval else 'NA',
            'Environment Clearance': project.environment_clearance if project.environment_clearance else 'NA',
            'ALMM Listing': project.almm_listing if project.almm_listing else 'NA',
            'Investment (USD Million)': project.investment_usd if project.investment_usd is not None else 0.0,
            'Investment (INR Billion)': project.investment_inr if project.investment_inr is not None else 0.0,
            'Expected Completion': project.expected_completion if project.expected_completion else 'NA',
            'Last Updated': project.last_updated.strftime('%d-%m-%Y') if project.last_updated else 'NA',
            'Source': project.source
        }
        
        # Create DataFrame
        df = pd.DataFrame([project_data])
        
        # Export to Excel
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=f'{project.type}_Project', index=False)
        
        logger.info(f"Single project exported to {filename}")
        return filename
        
    except Exception as e:
        logger.error(f"Error exporting single project: {str(e)}")
        raise
