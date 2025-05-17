import time
import logging
import threading
from app import db

logger = logging.getLogger(__name__)

class ProgressTracker:
    """Improved progress tracker with timeout and error handling"""
    
    def __init__(self):
        self.processed_sources = 0
        self.projects_added = 0
        self.is_completed = False
        self.is_in_progress = False
        self.error = None
        self.start_time = None
        self.max_time = 600  # 10 minutes max runtime
        self._lock = threading.Lock()
        
    def reset(self):
        """Reset the tracker to initial state"""
        with self._lock:
            self.processed_sources = 0
            self.projects_added = 0
            self.is_completed = False
            self.is_in_progress = True
            self.error = None
            self.start_time = time.time()
        
        # Start a watchdog thread to prevent endless running
        watchdog = threading.Thread(target=self._watchdog)
        watchdog.daemon = True
        watchdog.start()
        logger.info("Progress tracking started with watchdog")
        
    def _watchdog(self):
        """Watchdog thread to ensure processing completes"""
        while True:
            time.sleep(10)  # Check every 10 seconds
            with self._lock:
                if not self.is_in_progress:
                    return  # Exit if processing is done
                
                # Force completion if we exceed max time
                if self.start_time and (time.time() - self.start_time) > self.max_time:
                    logger.warning(f"Watchdog forcing completion after {self.max_time} seconds")
                    self.is_completed = True
                    self.is_in_progress = False
                    self.error = "Operation timed out"
                    return
        
    def complete(self):
        """Mark the process as complete"""
        with self._lock:
            logger.info(f"Progress tracking completed after processing {self.processed_sources} sources and adding {self.projects_added} projects")
            self.is_completed = True
            self.is_in_progress = False
        
    def increment_source(self):
        """Increment the count of processed sources"""
        with self._lock:
            self.processed_sources += 1
        
    def add_projects(self, count):
        """Add to the count of projects added"""
        with self._lock:
            self.projects_added += count
    
    def set_error(self, message):
        """Set an error message"""
        with self._lock:
            self.error = message
            logger.error(f"Progress tracker error: {message}")
            
    def get_state(self):
        """Get the current state as a dictionary"""
        with self._lock:
            return {
                'in_progress': self.is_in_progress,
                'completed': self.is_completed,
                'processed_sources': self.processed_sources,
                'projects_added': self.projects_added,
                'error': self.error,
                'elapsed': time.time() - self.start_time if self.start_time else 0
            }

# Create a global instance
progress = ProgressTracker()