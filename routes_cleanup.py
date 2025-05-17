from app import app, db, logger
from flask import flash, redirect, url_for, jsonify
from models import Project
import re
from cleanup_utility import cleanup_irrelevant_projects

@app.route('/cleanup-data', methods=['POST'])
def cleanup_data():
    """Clean up database by removing irrelevant projects based on strict criteria"""
    try:
        # Use the cleanup utility to perform the cleanup
        result = cleanup_irrelevant_projects()
        
        # Flash the appropriate message
        if result["success"]:
            if result["count"] > 0:
                flash(result["message"], 'success')
            else:
                flash(result["message"], 'info')
        else:
            flash(result["message"], 'danger')
            
        return redirect(url_for('projects'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during data cleanup: {str(e)}")
        flash(f'Error cleaning up data: {str(e)}', 'danger')
        return redirect(url_for('projects'))