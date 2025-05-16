from app import app, db, logger
from flask import flash, redirect, url_for
from models import Project
import re

@app.route('/cleanup-data', methods=['POST'])
def cleanup_data():
    """Clean up database by removing irrelevant projects based on strict criteria"""
    try:
        logger.info("Starting data cleanup process")
        # Filter criteria for likely invalid projects
        invalid_projects = 0
        
        # Define manufacturing-related terms that should be in valid projects
        manufacturing_terms = [
            'manufacturing', 'factory', 'production', 'facility', 'plant',
            'gigafactory', 'module production', 'cell production', 'manufacturing hub'
        ]
        
        # Define terms that indicate non-manufacturing content
        non_manufacturing_terms = [
            'exam', 'result', 'score', 'live', 'update', 'cricket', 'election',
            'festival', 'holiday', 'weather', 'review', 'interview', 'conference',
            'webinar', 'meeting', 'symposium', 'market update', 'opinion', 'editorial'
        ]
        
        projects_to_remove = []
        
        # Check all projects with more sophisticated filtering
        for project in Project.query.all():
            # Skip projects with significant manufacturing capacity values
            if (project.cell_capacity and project.cell_capacity > 0.1) or \
               (project.module_capacity and project.module_capacity > 0.1) or \
               (project.integration_capacity and project.integration_capacity > 0.1):
                continue
                
            # Skip projects with significant investment values
            if (project.investment_usd and project.investment_usd > 10) or \
               (project.investment_inr and project.investment_inr > 1):
                continue
            
            # Check for manufacturing terms in name and company
            has_manufacturing_term = False
            if project.name:
                has_manufacturing_term = any(term.lower() in project.name.lower() for term in manufacturing_terms)
            
            if project.company and not has_manufacturing_term:
                has_manufacturing_term = any(term.lower() in project.company.lower() for term in manufacturing_terms)
                
            if has_manufacturing_term:
                continue
                
            # Check for non-manufacturing terms that suggest irrelevant content
            has_non_manufacturing_term = False
            if project.name:
                has_non_manufacturing_term = any(term.lower() in project.name.lower() for term in non_manufacturing_terms)
                
            if has_non_manufacturing_term or not has_manufacturing_term:
                projects_to_remove.append(project)
                invalid_projects += 1
        
        # Delete the identified invalid projects
        for project in projects_to_remove:
            logger.info(f"Removing likely irrelevant project: {project.name}")
            db.session.delete(project)
            
        # Commit the changes if any projects were deleted
        if invalid_projects > 0:
            db.session.commit()
            flash(f'Successfully removed {invalid_projects} irrelevant projects from the database', 'success')
            logger.info(f"Cleanup complete: Removed {invalid_projects} irrelevant projects")
        else:
            flash('No irrelevant projects found to clean up', 'info')
            logger.info("Cleanup complete: No irrelevant projects found")
            
        return redirect(url_for('projects'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during data cleanup: {str(e)}")
        flash(f'Error cleaning up data: {str(e)}', 'danger')
        return redirect(url_for('projects'))