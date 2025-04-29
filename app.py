import os
import logging
import threading
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
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the app with the extension
db.init_app(app)

# Import routes after app initialization to avoid circular imports
from routes import *
import models  # Import models to register them with SQLAlchemy

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
