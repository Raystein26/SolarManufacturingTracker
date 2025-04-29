import logging
import time
import datetime
import threading
from app import app
from project_tracker import check_all_sources

logger = logging.getLogger(__name__)

# Attempt to import schedule
try:
    import schedule
    USE_SCHEDULE = True
    logger.info("Schedule module loaded successfully")
except ImportError:
    USE_SCHEDULE = False
    logger.warning("Schedule module not available. Falling back to manual scheduling.")


def run_scheduled_task():
    """Run the scheduled task to check all sources"""
    logger.info("Running scheduled check of all sources")
    with app.app_context():
        check_all_sources()
    logger.info("Scheduled check complete")


def scheduler_loop():
    """Main scheduler loop that runs continuously"""
    logger.info("Starting scheduler loop")
    
    while True:
        try:
            if USE_SCHEDULE:
                schedule.run_pending()
            else:
                # Simple time-based check if schedule module is not available
                current_hour = datetime.datetime.now().hour
                if current_hour == 6 or current_hour == 18:  # Run at 6 AM and 6 PM
                    run_scheduled_task()
            
            time.sleep(60)  # Check every minute
            
        except Exception as e:
            logger.error(f"Error in scheduler loop: {str(e)}")
            time.sleep(300)  # Wait 5 minutes if there's an error


def start_scheduler():
    """Initialize and start the scheduler"""
    try:
        if USE_SCHEDULE:
            # Schedule twice-daily checks
            schedule.every().day.at("06:00").do(run_scheduled_task)
            schedule.every().day.at("18:00").do(run_scheduled_task)
            
            logger.info("Scheduler initialized with daily checks at 06:00 and 18:00")
        else:
            logger.info("Using simple time-based scheduling (6 AM and 6 PM)")
        
        # Run the scheduler loop
        scheduler_loop()
        
    except Exception as e:
        logger.error(f"Error starting scheduler: {str(e)}")
