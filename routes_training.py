"""
Routes for training the renewable energy project detection system
"""

import os
import logging
import pandas as pd
from flask import Blueprint, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename
from datetime import datetime

from training_module import ProjectTypeTrainer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a blueprint for training routes
training_bp = Blueprint('training_bp', __name__, url_prefix='/training')

# Initialize trainer
trainer = ProjectTypeTrainer()

@training_bp.route('/', methods=['GET'])
def training_dashboard():
    """Render the training dashboard page"""
    from datetime import datetime
    return render_template('training.html', datetime=datetime)

@training_bp.route('/api/stats', methods=['GET'])
def get_training_stats():
    """Get current training statistics"""
    try:
        # Load training data
        training_data = trainer.get_training_results()
        
        # Format stats from training data
        stats = {}
        
        for project_type, data in training_data.items():
            stats[project_type] = {
                'keywords': data.get('keywords', []),
                'examples': len(data.get('keywords', [])) // 3,  # Rough estimation
                'phrases': data.get('phrases', [])
            }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error getting training stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@training_bp.route('/api/upload', methods=['POST'])
def upload_training_file():
    """Upload and process a training Excel file"""
    try:
        if 'training_file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            })
        
        file = request.files['training_file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            })
        
        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({
                'success': False,
                'error': 'File must be an Excel file (.xlsx or .xls)'
            })
        
        # Save file with timestamp to avoid overwriting
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"training_data_{timestamp}.xlsx"
        file_path = os.path.join(os.getcwd(), filename)
        
        file.save(file_path)
        logger.info(f"Saved training file to {file_path}")
        
        # Process the training file
        trainer.process_excel_file(file_path)
        
        # Get training results to return to frontend
        training_results = trainer.get_training_results()
        
        return jsonify({
            'success': True,
            'message': f"Training file processed successfully with {len(training_results)} categories",
            'training_results': training_results
        })
        
    except Exception as e:
        logger.error(f"Error processing training file: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@training_bp.route('/api/sample', methods=['GET'])
def download_sample_file():
    """Download a sample training template"""
    try:
        # Create a sample DataFrame with examples of different renewable energy types
        data = {
            'Type': ['Solar', 'Solar', 'Wind', 'Wind', 'Battery', 'Battery', 
                     'Hydro', 'Hydro', 'Hydrogen', 'Hydrogen', 'Biofuel', 'Biofuel'],
            'Name': ['Adani Solar Module Manufacturing Project', 'NTPC 500MW Solar Park Gujarat',
                     'Suzlon 250MW Wind Farm Tamil Nadu', 'ReNew Power Offshore Wind Project',
                     'Tata Battery Storage Project Mumbai', 'Exide Cell Manufacturing Facility',
                     'NHPC Small Hydro Project Himachal', 'Pumped Storage Hydro Project Karnataka',
                     'Reliance Green Hydrogen Project Gujarat', 'NTPC Electrolyzer Plant',
                     'Indian Oil Ethanol Production Facility', 'Praj Biofuel Project Maharashtra'],
            'Company': ['Adani Green', 'NTPC', 
                        'Suzlon', 'ReNew Power', 
                        'Tata Power', 'Exide', 
                        'NHPC', 'JSW Energy', 
                        'Reliance', 'NTPC', 
                        'Indian Oil', 'Praj Industries'],
            'State': ['Gujarat', 'Gujarat', 
                      'Tamil Nadu', 'Gujarat', 
                      'Maharashtra', 'Karnataka', 
                      'Himachal Pradesh', 'Karnataka', 
                      'Gujarat', 'Rajasthan', 
                      'Uttar Pradesh', 'Maharashtra'],
            'Location': ['Mundra', 'Kutch', 
                         'Tuticorin', 'Gulf of Khambhat', 
                         'Mumbai', 'Bangalore', 
                         'Kullu', 'Sharavathi', 
                         'Jamnagar', 'Jaipur', 
                         'Mathura', 'Pune'],
            'Category': ['Manufacturing', 'Generation', 
                         'Generation', 'Generation', 
                         'Storage', 'Manufacturing', 
                         'Generation', 'Storage', 
                         'Production', 'Manufacturing', 
                         'Production', 'Production'],
            'Investment (USD Million)': [2000, 450, 
                                         300, 800, 
                                         500, 1200, 
                                         150, 600, 
                                         800, 300, 
                                         200, 150],
            'Generation Capacity (GW)': [3.0, 0.5, 
                                         0.25, 1.0, 
                                         None, None, 
                                         0.1, 1.2, 
                                         None, None, 
                                         None, None],
            'Storage Capacity (GWh)': [None, None, 
                                       None, None, 
                                       2.0, 5.0, 
                                       None, 8.0, 
                                       None, None, 
                                       None, None],
            'Hydrogen Production (tons/day)': [None, None, 
                                              None, None, 
                                              None, None, 
                                              None, None, 
                                              25, 10, 
                                              None, None],
            'Biofuel Capacity (million liters/year)': [None, None, 
                                                       None, None, 
                                                       None, None, 
                                                       None, None, 
                                                       None, None, 
                                                       500, 350]
        }
        
        df = pd.DataFrame(data)
        
        # Save to a temporary file
        sample_file = 'renewable_project_sample_template.xlsx'
        df.to_excel(sample_file, index=False)
        
        # Send the file
        return send_file(sample_file, 
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True,
                         download_name='renewable_project_sample_template.xlsx')
        
    except Exception as e:
        logger.error(f"Error creating sample file: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })