import flask
from flask import render_template, request, jsonify, flash, redirect, url_for, send_file
from app import app, db, logger
from models import Project, Source, NewsArticle, ScrapeLog
from project_tracker import run_manual_check
from data_manager import export_to_excel, import_from_excel
import os
import pandas as pd
from datetime import datetime
import threading

@app.route('/')
def index():
    # Get summary statistics for all renewable energy categories
    solar_count = Project.query.filter_by(type='Solar').count()
    battery_count = Project.query.filter_by(type='Battery').count()
    wind_count = Project.query.filter_by(type='Wind').count()
    hydro_count = Project.query.filter_by(type='Hydro').count()
    hydrogen_count = Project.query.filter(Project.type.in_(['Green Hydrogen', 'GreenHydrogen'])).count()
    biofuel_count = Project.query.filter_by(type='Biofuel').count()
    sources_count = Source.query.count()
    
    # Total projects count
    total_count = solar_count + battery_count + wind_count + hydro_count + hydrogen_count + biofuel_count
    
    # Recent projects
    recent_projects = Project.query.order_by(Project.created_at.desc()).limit(5).all()
    
    # Summary by state
    state_summary = db.session.query(
        Project.state, 
        db.func.count(Project.id).label('count')
    ).group_by(Project.state).all()
    
    return render_template('index.html', 
                          solar_count=solar_count,
                          battery_count=battery_count,
                          wind_count=wind_count,
                          hydro_count=hydro_count,
                          hydrogen_count=hydrogen_count,
                          biofuel_count=biofuel_count,
                          total_count=total_count,
                          sources_count=sources_count,
                          recent_projects=recent_projects,
                          state_summary=state_summary,
                          datetime=datetime)

@app.route('/dashboard')
def dashboard():
    # Get projects by type and status
    projects_by_type = db.session.query(
        Project.type, 
        db.func.count(Project.id).label('count')
    ).group_by(Project.type).all()
    
    projects_by_status = db.session.query(
        Project.status, 
        db.func.count(Project.id).label('count')
    ).group_by(Project.status).all()
    
    # Projects by state
    projects_by_state = db.session.query(
        Project.state, 
        db.func.count(Project.id).label('count')
    ).group_by(Project.state).order_by(db.func.count(Project.id).desc()).all()
    
    # Get all project types
    project_types = db.session.query(Project.type, db.func.count(Project.id)).group_by(Project.type).all()
    
    # Total capacity by type for all renewable energy categories
    solar_capacity = db.session.query(db.func.sum(Project.generation_capacity)).filter_by(type='Solar').scalar() or 0
    wind_capacity = db.session.query(db.func.sum(Project.generation_capacity)).filter_by(type='Wind').scalar() or 0
    hydro_capacity = db.session.query(db.func.sum(Project.generation_capacity)).filter_by(type='Hydro').scalar() or 0
    storage_capacity = db.session.query(db.func.sum(Project.storage_capacity)).filter_by(type='Battery').scalar() or 0
    
    # Handle both "Green Hydrogen" and "GreenHydrogen" variations
    hydrogen_capacity = (
        db.session.query(db.func.sum(Project.electrolyzer_capacity))
        .filter(Project.type.in_(['Green Hydrogen', 'GreenHydrogen']))
        .scalar() or 0
    )
    
    biofuel_capacity = db.session.query(db.func.sum(Project.biofuel_capacity)).filter_by(type='Biofuel').scalar() or 0
    
    # Recent scrape logs
    recent_logs = ScrapeLog.query.order_by(ScrapeLog.timestamp.desc()).limit(10).all()
    
    return render_template('dashboard.html',
                          projects_by_type=projects_by_type,
                          projects_by_status=projects_by_status,
                          projects_by_state=projects_by_state,
                          solar_capacity=solar_capacity,
                          wind_capacity=wind_capacity,
                          hydro_capacity=hydro_capacity,
                          storage_capacity=storage_capacity,
                          hydrogen_capacity=hydrogen_capacity,
                          biofuel_capacity=biofuel_capacity,
                          recent_logs=recent_logs,
                          datetime=datetime)

@app.route('/projects')
def projects():
    project_type = request.args.get('type', 'all')
    
    if project_type.lower() == 'solar':
        projects = Project.query.filter_by(type='Solar').order_by(Project.created_at.desc()).all()
    elif project_type.lower() == 'battery':
        projects = Project.query.filter_by(type='Battery').order_by(Project.created_at.desc()).all()
    else:
        projects = Project.query.order_by(Project.created_at.desc()).all()
    
    return render_template('projects.html', projects=projects, project_type=project_type, datetime=datetime)

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('project_detail.html', project=project, datetime=datetime)

@app.route('/sources')
def sources():
    sources = Source.query.all()
    return render_template('sources.html', sources=sources, datetime=datetime)

@app.route('/source/<int:source_id>')
def source_detail(source_id):
    source = Source.query.get_or_404(source_id)
    articles = NewsArticle.query.filter_by(source_id=source.id).order_by(NewsArticle.created_at.desc()).all()
    logs = ScrapeLog.query.filter_by(source_id=source.id).order_by(ScrapeLog.timestamp.desc()).all()
    
    return render_template('source_detail.html', source=source, articles=articles, logs=logs, datetime=datetime)

@app.route('/about')
def about():
    return render_template('about.html', datetime=datetime)

@app.route('/api/projects')
def api_projects():
    project_type = request.args.get('type', 'all')
    
    if project_type.lower() == 'solar':
        projects = Project.query.filter_by(type='Solar').all()
    elif project_type.lower() == 'battery':
        projects = Project.query.filter_by(type='Battery').all()
    else:
        projects = Project.query.all()
    
    return jsonify([project.to_dict() for project in projects])

@app.route('/api/sources')
def api_sources():
    sources = Source.query.all()
    return jsonify([{
        'id': source.id,
        'url': source.url,
        'name': source.name,
        'description': source.description,
        'last_checked': source.last_checked.strftime('%Y-%m-%d %H:%M:%S') if source.last_checked else None,
        'status': source.status
    } for source in sources])

@app.route('/api/run-check', methods=['POST'])
def api_run_check():
    try:
        # Import here to avoid circular imports
        from project_tracker import progress, initialize_sources
        
        # First ensure all sources are initialized
        with app.app_context():
            logger.info("Running initialize_sources from api_run_check")
            initialize_sources()
        
        # Run the check in a background thread
        thread = threading.Thread(target=run_check_with_progress)
        thread.daemon = True
        thread.start()
        return jsonify({'status': 'success', 'message': 'Check started in background'})
    except Exception as e:
        logger.error(f"Error starting manual check: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

def run_check_with_progress():
    """Run manual check with progress tracking"""
    try:
        # Initialize sources to make sure all new sources are included
        from project_tracker import initialize_sources
        with app.app_context():
            initialize_sources()
            
        # Get the result from the manual check
        result = run_manual_check()
        return result
    except Exception as e:
        logger.error(f"Error in run_check_with_progress: {str(e)}")
        # Import here to avoid circular imports
        from project_tracker import progress
        progress.complete()  # Mark as completed even on error
        return {"status": "error", "message": str(e)}

@app.route('/api/check-progress', methods=['GET'])
def api_check_progress():
    """Get the current progress of the scraping process"""
    # Import here to avoid circular imports
    from progress_tracker import progress
    
    try:
        # Get the total sources count
        total_sources = Source.query.count()
        
        # Get state from the progress tracker
        state = progress.get_state()
        
        return jsonify({
            'in_progress': state['in_progress'],
            'processed_sources': state['processed_sources'],
            'total_sources': total_sources,
            'projects_added': state['projects_added'],
            'completed': state['completed'],
            'error': state.get('error')
        })
    except Exception as e:
        logger.error(f"Error checking progress: {str(e)}")
        return jsonify({
            'in_progress': False,
            'processed_sources': 0,
            'total_sources': 0,
            'projects_added': 0,
            'completed': True,
            'error': f"Error checking progress: {str(e)}"
        })

@app.route('/api/export-excel', methods=['GET'])
def api_export_excel():
    try:
        filename = export_to_excel()
        # Return the file path so frontend knows where to download from
        return jsonify({'status': 'success', 'filename': f'/download-excel/{filename}'})
    except Exception as e:
        logger.error(f"Error exporting to Excel: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/download-excel/<path:filename>', methods=['GET'])
def download_excel(filename):
    """Download the generated Excel file"""
    try:
        # Return the Excel file as an attachment
        return flask.send_from_directory(
            directory=".",  # Current directory where the file is saved
            path=filename,
            as_attachment=True
        )
    except Exception as e:
        logger.error(f"Error downloading Excel file: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/import-excel', methods=['POST'])
def api_import_excel():
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file part'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No selected file'})
        
        if file and file.filename.endswith('.xlsx'):
            # Save the file temporarily
            temp_path = 'temp_import.xlsx'
            file.save(temp_path)
            
            # Import the data
            result = import_from_excel(temp_path)
            
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            return jsonify({'status': 'success', 'message': result})
        else:
            return jsonify({'status': 'error', 'message': 'Invalid file format. Please upload an Excel file.'})
    
    except Exception as e:
        logger.error(f"Error importing from Excel: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/add-source', methods=['GET', 'POST'])
def add_source():
    if request.method == 'POST':
        url = request.form.get('url')
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not url:
            flash('URL is required', 'danger')
            return redirect(url_for('add_source'))
        
        # Check if source already exists
        existing_source = Source.query.filter_by(url=url).first()
        if existing_source:
            flash('Source with this URL already exists', 'warning')
            return redirect(url_for('sources'))
        
        # Add new source
        new_source = Source(
            url=url,
            name=name,
            description=description,
            created_at=datetime.utcnow()
        )
        
        db.session.add(new_source)
        db.session.commit()
        
        flash('Source added successfully', 'success')
        return redirect(url_for('sources'))
    
    return render_template('add_source.html', datetime=datetime)

@app.route('/add-project', methods=['GET', 'POST'])
def add_project():
    if request.method == 'POST':
        try:
            # Extract data from form
            project_type = request.form.get('type')
            name = request.form.get('name')
            company = request.form.get('company')
            ownership = request.form.get('ownership')
            pli_status = request.form.get('pli_status')
            state = request.form.get('state')
            location = request.form.get('location')
            
            # Date handling
            announcement_date_str = request.form.get('announcement_date')
            announcement_date = datetime.strptime(announcement_date_str, '%Y-%m-%d') if announcement_date_str else None
            
            category = request.form.get('category')
            input_type = request.form.get('input_type')
            output_type = request.form.get('output_type')
            
            # Convert capacity to float
            cell_capacity = float(request.form.get('cell_capacity', 0) or 0)
            module_capacity = float(request.form.get('module_capacity', 0) or 0)
            integration_capacity = float(request.form.get('integration_capacity', 0) or 0)
            
            status = request.form.get('status')
            land_acquisition = request.form.get('land_acquisition')
            power_approval = request.form.get('power_approval')
            environment_clearance = request.form.get('environment_clearance')
            almm_listing = request.form.get('almm_listing')
            
            # Convert investment to float
            investment_usd = float(request.form.get('investment_usd', 0) or 0)
            investment_inr = float(request.form.get('investment_inr', 0) or 0)
            
            expected_completion = request.form.get('expected_completion')
            source = request.form.get('source')
            
            # Calculate the next index
            max_index = db.session.query(db.func.max(Project.index)).scalar() or 0
            next_index = max_index + 1
            
            # Create new project
            new_project = Project(
                index=next_index,
                type=project_type,
                name=name,
                company=company,
                ownership=ownership,
                pli_status=pli_status,
                state=state,
                location=location,
                announcement_date=announcement_date,
                category=category,
                input_type=input_type,
                output_type=output_type,
                cell_capacity=cell_capacity,
                module_capacity=module_capacity,
                integration_capacity=integration_capacity,
                status=status,
                land_acquisition=land_acquisition,
                power_approval=power_approval,
                environment_clearance=environment_clearance,
                almm_listing=almm_listing,
                investment_usd=investment_usd,
                investment_inr=investment_inr,
                expected_completion=expected_completion,
                last_updated=datetime.utcnow().date(),
                source=source
            )
            
            db.session.add(new_project)
            db.session.commit()
            
            flash('Project added successfully', 'success')
            return redirect(url_for('projects'))
            
        except Exception as e:
            logger.error(f"Error adding project: {str(e)}")
            flash(f'Error adding project: {str(e)}', 'danger')
            return redirect(url_for('add_project'))
    
    return render_template('add_project.html', datetime=datetime)

@app.route('/api/project/<int:project_id>/delete', methods=['DELETE'])
def delete_project(project_id):
    """Delete a specific project"""
    try:
        project = Project.query.get_or_404(project_id)
        project_name = project.name
        
        db.session.delete(project)
        db.session.commit()
        
        logger.info(f"Project deleted: {project_name} (ID: {project_id})")
        return jsonify({'success': True, 'message': 'Project deleted successfully'})
        
    except Exception as e:
        logger.error(f"Error deleting project {project_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/project/<int:project_id>/export')
def export_single_project(project_id):
    """Export a single project to Excel"""
    try:
        from data_manager import export_single_project_to_excel
        
        project = Project.query.get_or_404(project_id)
        filename = export_single_project_to_excel(project)
        
        return send_file(filename, as_attachment=True, download_name=f"project_{project_id}_{project.name[:30].replace(' ', '_')}.xlsx")
        
    except Exception as e:
        logger.error(f"Error exporting project {project_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/project/<int:project_id>/edit', methods=['GET', 'POST'])
def edit_project(project_id):
    """Edit a specific project"""
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        try:
            # Update project fields from form data
            project.name = request.form.get('name', project.name)
            project.company = request.form.get('company', project.company)
            project.type = request.form.get('type', project.type)
            project.state = request.form.get('state', project.state)
            project.location = request.form.get('location', project.location)
            project.status = request.form.get('status', project.status)
            project.expected_completion = request.form.get('expected_completion', project.expected_completion)
            
            # Handle capacity fields based on project type
            if project.type in ['Solar', 'Battery']:
                if request.form.get('cell_capacity'):
                    project.cell_capacity = float(request.form.get('cell_capacity', 0))
                if request.form.get('module_capacity'):
                    project.module_capacity = float(request.form.get('module_capacity', 0))
                if request.form.get('integration_capacity'):
                    project.integration_capacity = float(request.form.get('integration_capacity', 0))
            
            # Handle investment fields
            if request.form.get('investment_usd'):
                project.investment_usd = float(request.form.get('investment_usd', 0))
            if request.form.get('investment_inr'):
                project.investment_inr = float(request.form.get('investment_inr', 0))
            
            project.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash('Project updated successfully', 'success')
            return redirect(url_for('project_detail', project_id=project.id))
            
        except Exception as e:
            logger.error(f"Error updating project {project_id}: {str(e)}")
            flash(f'Error updating project: {str(e)}', 'danger')
    
    return render_template('edit_project.html', project=project, datetime=datetime)
