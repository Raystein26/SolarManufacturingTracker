import os
import logging
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("project_tracker.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # Needed for url_for to generate with https

# Configure the PostgreSQL database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
    "pool_timeout": 30,  # Timeout for getting a connection from the pool
    "max_overflow": 10,  # Maximum number of connections to overflow from the pool
    "pool_size": 5       # The size of the connection pool
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Application feature flags
app.config["DIAGNOSTIC_MODE"] = True  # Enable diagnostic mode to track potential projects

# Initialize the app with the extension
db.init_app(app)

# Make datetime available in all templates
@app.context_processor
def inject_datetime():
    return {'datetime': datetime}

# Import routes after app initialization to avoid circular imports
from routes import *
import models  # Import models to register them with SQLAlchemy

# Import diagnostic routes
try:
    from routes_diagnostic import diagnostic_bp
    app.register_blueprint(diagnostic_bp)
    logger.info("Diagnostic routes registered successfully")
except ImportError:
    logger.warning("Diagnostic routes could not be registered")

# Import training routes
try:
    from routes_training import training_bp
    app.register_blueprint(training_bp)
    logger.info("Training routes registered successfully")
except ImportError:
    logger.warning("Training routes could not be registered")

# Initialize database
with app.app_context():
    db.create_all()

# Import and start the scheduler in a separate thread
from scheduler import start_scheduler

# Instead of @app.before_first_request which is deprecated
def initialize_scheduler():
    # Start the scheduler in a separate thread
    thread = threading.Thread(target=start_scheduler)
    thread.daemon = True
    thread.start()
    logger.info("Scheduler started in background thread")

# Register a function that runs when the app context is created
@app.before_request
def before_request():
    # Use a global variable to track if scheduler has been initialized
    if not getattr(app, 'scheduler_started', False):
        initialize_scheduler()
        app.scheduler_started = True

# Add global error handlers for database connection issues
@app.errorhandler(500)
def handle_server_error(e):
    logger.error(f"500 error: {str(e)}")
    if "database" in str(e).lower() or "sql" in str(e).lower() or "connection" in str(e).lower():
        return render_template('error.html', error="Database connection error. Please try again later."), 500
    return render_template('error.html', error="An unexpected error occurred. Please try again later."), 500
