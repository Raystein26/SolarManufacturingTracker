from app import db, logger
from models import Project

def cleanup_irrelevant_projects():
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
            logger.info(f"Cleanup complete: Removed {invalid_projects} irrelevant projects")
            return {"success": True, "message": f"Successfully removed {invalid_projects} irrelevant projects", "count": invalid_projects}
        else:
            logger.info("Cleanup complete: No irrelevant projects found")
            return {"success": True, "message": "No irrelevant projects found to clean up", "count": 0}
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during data cleanup: {str(e)}")
        return {"success": False, "message": f"Error cleaning up data: {str(e)}", "count": 0}