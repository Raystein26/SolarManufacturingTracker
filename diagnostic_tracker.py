"""
Diagnostic tracker for monitoring pipeline projects with lower confidence thresholds
This module helps identify projects that are being missed by the regular scraper
"""
import logging
import json
import os
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

class DiagnosticTracker:
    """Diagnostic tracker for monitoring potential projects with lower confidence thresholds"""
    
    def __init__(self, diagnostic_file="diagnostic_data.json"):
        """Initialize the diagnostic tracker"""
        self.diagnostic_file = diagnostic_file
        self.potential_projects = []
        self.load_diagnostics()
    
    def load_diagnostics(self):
        """Load existing diagnostic data if available"""
        try:
            if os.path.exists(self.diagnostic_file):
                with open(self.diagnostic_file, 'r') as f:
                    data = json.load(f)
                    self.potential_projects = data.get('potential_projects', [])
                    logger.info(f"Loaded {len(self.potential_projects)} potential projects from diagnostic file")
        except Exception as e:
            logger.error(f"Error loading diagnostic data: {e}")
            self.potential_projects = []
    
    def save_diagnostics(self):
        """Save diagnostic data to file"""
        try:
            with open(self.diagnostic_file, 'w') as f:
                json.dump({
                    'potential_projects': self.potential_projects,
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
                logger.info(f"Saved {len(self.potential_projects)} potential projects to diagnostic file")
        except Exception as e:
            logger.error(f"Error saving diagnostic data: {e}")
    
    def track_potential_project(self, article_url, title, content_snippet, scores, reason):
        """
        Track a potential project that doesn't meet current confidence thresholds
        
        Args:
            article_url: URL of the article
            title: Title of the article
            content_snippet: Short content snippet (first 500 chars)
            scores: Dictionary of scores for each project type
            reason: Reason why the project was rejected
        """
        # Create snippet of content (first 500 chars)
        if len(content_snippet) > 500:
            content_snippet = content_snippet[:497] + "..."
        
        # Format scores for better readability
        formatted_scores = {}
        for category, score in scores.items():
            formatted_scores[category] = round(float(score), 2)
        
        # Add to potential projects list
        self.potential_projects.append({
            'url': article_url,
            'title': title,
            'content_snippet': content_snippet,
            'scores': formatted_scores,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
        
        # Save immediately to avoid losing data
        self.save_diagnostics()
        
        logger.info(f"Tracked potential project: {title} (Reason: {reason})")
    
    def get_potential_projects(self, limit=20):
        """Get list of potential projects, newest first"""
        return sorted(
            self.potential_projects, 
            key=lambda x: x.get('timestamp', ''), 
            reverse=True
        )[:limit]
    
    def get_stats(self):
        """Get statistics about potential projects"""
        if not self.potential_projects:
            return {
                'total': 0,
                'rejection_reasons': {},
                'top_categories': {}
            }
        
        # Count rejection reasons
        reasons = {}
        for project in self.potential_projects:
            reason = project.get('reason', 'Unknown')
            reasons[reason] = reasons.get(reason, 0) + 1
        
        # Find top categories based on scores
        categories = {}
        for project in self.potential_projects:
            scores = project.get('scores', {})
            if scores:
                top_category = max(scores.items(), key=lambda x: x[1])[0]
                categories[top_category] = categories.get(top_category, 0) + 1
        
        return {
            'total': len(self.potential_projects),
            'rejection_reasons': reasons,
            'top_categories': categories
        }

# Create a global instance for easy import
diagnostic_tracker = DiagnosticTracker()