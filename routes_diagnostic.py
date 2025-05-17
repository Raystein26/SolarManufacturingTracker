"""
Routes for diagnostic information about potential renewable energy projects
"""
import logging
from flask import Blueprint, jsonify, render_template
from app import app

# Create a logger for this module
logger = logging.getLogger(__name__)

# Try to import the diagnostic tracker
try:
    from diagnostic_tracker import diagnostic_tracker
    DIAGNOSTIC_MODE = True
except ImportError:
    DIAGNOSTIC_MODE = False
    logger.warning("Diagnostic tracker not available - diagnostic routes will have limited functionality")

# Create a blueprint for diagnostic routes with a unique name
diagnostic_bp = Blueprint('diagnostic_blueprint', __name__, url_prefix='/diagnostic')

@diagnostic_bp.route('/api/stats', methods=['GET'])
def api_diagnostic_stats():
    """Get diagnostic statistics about potential missed projects"""
    if not DIAGNOSTIC_MODE:
        return jsonify({
            'error': 'Diagnostic mode is not enabled',
            'enabled': False
        })
    
    try:
        stats = diagnostic_tracker.get_stats()
        return jsonify({
            'success': True,
            'enabled': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error getting diagnostic stats: {e}")
        return jsonify({
            'error': str(e),
            'enabled': True
        })

@diagnostic_bp.route('/api/diagnostic/potential_projects', methods=['GET'])
def api_potential_projects():
    """Get a list of potential projects that didn't meet the confidence thresholds"""
    if not DIAGNOSTIC_MODE:
        return jsonify({
            'error': 'Diagnostic mode is not enabled',
            'enabled': False
        })
    
    try:
        projects = diagnostic_tracker.get_potential_projects()
        return jsonify({
            'success': True,
            'enabled': True,
            'projects': projects
        })
    except Exception as e:
        logger.error(f"Error getting potential projects: {e}")
        return jsonify({
            'error': str(e),
            'enabled': True
        })

@diagnostic_bp.route('/diagnostic', methods=['GET'])
def diagnostic_dashboard():
    """Render the diagnostic dashboard page"""
    diagnostic_enabled = DIAGNOSTIC_MODE
    return render_template('diagnostic.html', diagnostic_enabled=diagnostic_enabled)

# Register the blueprint with the app
app.register_blueprint(diagnostic_bp)