from app import db, logger
from models import Project

def cleanup_irrelevant_projects():
    """Clean up database by removing irrelevant projects based on strict criteria"""
    import re
    
    try:
        logger.info("Starting comprehensive cleanup of irrelevant projects")
        
        # Define patterns for irrelevant content
        irrelevant_patterns = [
            # Interview/discussion content
            r'(?i)interview|discussion|q&a|conversation|chat|talks?\s+to|speaks?\s+to',
            r'(?i)leading\s+with|vision\s+for|champions?|missing\s+link',
            r'(?i)economic\s+impact|downtime\s+to\s+downgrade|transformation\s+in',
            r'(?i)revving\s+up|fuelled\s+by|targeting\s+europe|global\s+ev\s+space',
            
            # Events/conferences
            r'(?i)podcast|webinar|event|conference|summit|conclave|roundtable',
            r'(?i)opinion|commentary|analysis|perspective|outlook|trends?',
            
            # General energy discussions without specific projects
            r'(?i)energy\s+transition|renewable\s+energy\s+sector|clean\s+energy\s+space',
            r'(?i)output\s+hits|energy\s+output|quarterly\s+results|annual\s+report',
            
            # Technology discussions without infrastructure projects
            r'(?i)explained|breaking\s+down|panel\s+triad|tech\s+trends',
            
            # Legal/regulatory content
            r'(?i)landmark\s+case|legal\s+ruling|court\s+decision|cleared\s+in',
            r'(?i)climate\s+case|brought\s+by|farmer'
        ]
        
        # Define terms that indicate actual infrastructure projects
        infrastructure_indicators = [
            'mw project', 'gw project', 'mwh project', 'gwh project',
            'tender', 'epc', 'secures', 'awarded', 'construction',
            'commissioning', 'operational', 'ground breaking',
            'foundation stone', 'inaugurate', 'plant', 'facility'
        ]
        
        projects_to_remove = []
        
        for project in Project.query.all():
            project_name = project.name or ""
            project_source = project.source or ""
            
            # Check for irrelevant patterns
            is_irrelevant = False
            for pattern in irrelevant_patterns:
                if re.search(pattern, project_name) or re.search(pattern, project_source):
                    is_irrelevant = True
                    break
            
            # Check if it's a proper infrastructure project
            has_infrastructure_indicators = any(
                indicator in project_name.lower() or indicator in project_source.lower()
                for indicator in infrastructure_indicators
            )
            
            # Check for valid capacity or investment data
            has_valid_capacity = (
                (project.generation_capacity and project.generation_capacity > 0) or
                (project.storage_capacity and project.storage_capacity > 0) or
                (project.electrolyzer_capacity and project.electrolyzer_capacity > 0) or
                (project.biofuel_capacity and project.biofuel_capacity > 0) or
                (project.cell_capacity and project.cell_capacity > 0) or
                (project.module_capacity and project.module_capacity > 0)
            )
            
            has_valid_investment = project.investment_usd and project.investment_usd > 0
            
            # Check for generic or problematic names
            problematic_terms = [
                "india's renewable energy", "renewable energy output", "energy output hits",
                "leading with topcon", "teri champions", "revving up", "missing link",
                "economic impact", "downtime to downgrade", "explained breaking down"
            ]
            
            has_problematic_name = any(term in project_name.lower() for term in problematic_terms)
            
            # Decide whether to remove the project
            should_remove = (
                is_irrelevant or 
                has_problematic_name or
                (not has_infrastructure_indicators and not has_valid_capacity and not has_valid_investment) or
                (len(project_name) < 15 and not has_valid_capacity and not has_valid_investment)
            )
            
            if should_remove:
                projects_to_remove.append(project)
        
        # Remove identified projects
        removed_count = 0
        for project in projects_to_remove:
            logger.info(f"Removing irrelevant project: {project.name[:50]}...")
            db.session.delete(project)
            removed_count += 1
        
        # Commit changes
        if removed_count > 0:
            db.session.commit()
            logger.info(f"Cleanup complete: Removed {removed_count} irrelevant projects")
            return {"success": True, "message": f"Successfully removed {removed_count} irrelevant projects", "count": removed_count}
        else:
            logger.info("Cleanup complete: No irrelevant projects found")
            return {"success": True, "message": "No irrelevant projects found to clean up", "count": 0}
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during cleanup: {str(e)}")
        return {"success": False, "message": f"Error cleaning up data: {str(e)}", "count": 0}