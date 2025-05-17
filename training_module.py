"""
Training module for enhancing renewable energy project type detection.
Uses existing project examples from Excel files to improve category recognition.
"""

import os
import logging
import pandas as pd
import re
from datetime import datetime
from collections import defaultdict
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProjectTypeTrainer:
    """
    Trainer for enhancing renewable energy project type detection.
    Analyzes Excel files with project examples to extract terminology and patterns.
    """
    
    def __init__(self, training_data_file=None):
        """Initialize the trainer with optional training data file"""
        self.training_data_path = "training_data.json"
        self.category_patterns = defaultdict(list)
        self.category_keywords = defaultdict(set)
        self.category_phrases = defaultdict(set)
        self.category_metrics = defaultdict(dict)
        
        # Load existing training data if available
        self.load_training_data()
        
        # If a training file is provided, process it
        if training_data_file:
            self.process_excel_file(training_data_file)
    
    def load_training_data(self):
        """Load existing training data if available"""
        if os.path.exists(self.training_data_path):
            try:
                with open(self.training_data_path, 'r') as f:
                    data = json.load(f)
                    
                # Convert defaultdict and sets from json representation
                self.category_keywords = {k: set(v) for k, v in data.get('keywords', {}).items()}
                self.category_phrases = {k: set(v) for k, v in data.get('phrases', {}).items()}
                self.category_patterns = defaultdict(list, data.get('patterns', {}))
                self.category_metrics = defaultdict(dict, data.get('metrics', {}))
                
                logger.info(f"Loaded training data with {len(self.category_keywords)} categories")
            except Exception as e:
                logger.error(f"Error loading training data: {e}")
    
    def save_training_data(self):
        """Save training data to file"""
        try:
            # Convert sets to lists for JSON serialization
            data = {
                'keywords': {k: list(v) for k, v in self.category_keywords.items()},
                'phrases': {k: list(v) for k, v in self.category_phrases.items()},
                'patterns': dict(self.category_patterns),
                'metrics': dict(self.category_metrics)
            }
            
            with open(self.training_data_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved training data to {self.training_data_path}")
        except Exception as e:
            logger.error(f"Error saving training data: {e}")
    
    def process_excel_file(self, excel_file):
        """Process an Excel file with project examples"""
        try:
            df = pd.read_excel(excel_file)
            
            # Normalize column names (handle different casing)
            df.columns = [col.lower() for col in df.columns]
            
            # Check for required columns
            required_cols = ['type', 'name', 'company', 'category']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                logger.warning(f"Missing required columns: {missing_cols}")
                # Try alternative column names
                mapping = {
                    'type': ['Type', 'project_type', 'energy_type'],
                    'name': ['Name', 'project_name'],
                    'company': ['Company', 'organization', 'developer'],
                    'category': ['Category', 'project_category']
                }
                
                for col in missing_cols:
                    for alt in mapping.get(col, []):
                        if alt in df.columns:
                            df[col] = df[alt]
                            logger.info(f"Using {alt} for {col}")
                            break
            
            # Check if we still have type column
            if 'type' not in df.columns:
                logger.error("Could not find 'type' column in Excel file")
                return
            
            # Extract patterns for each project type
            project_types = df['type'].unique()
            logger.info(f"Found {len(project_types)} project types: {project_types}")
            
            # Process each project type
            for project_type in project_types:
                if pd.isna(project_type):
                    continue
                    
                project_type = project_type.strip().lower()
                type_df = df[df['type'].str.lower() == project_type]
                
                logger.info(f"Processing {len(type_df)} examples for {project_type}")
                
                # Extract keywords from project names
                for _, row in type_df.iterrows():
                    self._extract_keywords(project_type, row)
                    self._extract_metrics(project_type, row)
            
            # After processing all examples, save the training data
            self.save_training_data()
            
        except Exception as e:
            logger.error(f"Error processing Excel file {excel_file}: {e}")
    
    def _extract_keywords(self, project_type, row):
        """Extract keywords from a project example"""
        # Process name
        if 'name' in row and pd.notna(row['name']):
            name = str(row['name']).lower()
            
            # Add project name keywords
            keywords = set(re.findall(r'\b\w+\b', name))
            self.category_keywords[project_type].update(keywords)
            
            # Capture multi-word phrases that might be important
            phrases = re.findall(r'\b\w+\s+\w+\b', name)
            self.category_phrases[project_type].update(phrases)
        
        # Process company name for additional context
        if 'company' in row and pd.notna(row['company']):
            company = str(row['company']).lower()
            # Companies often specialize in specific renewable types
            self.category_keywords[project_type].add(company)
        
        # Process category for additional dimensions
        if 'category' in row and pd.notna(row['category']):
            category = str(row['category']).lower()
            self.category_keywords[project_type].add(category)
    
    def _extract_metrics(self, project_type, row):
        """Extract metric patterns from a project example"""
        # Different metrics for different project types
        metric_fields = {
            'solar': ['generation_capacity', 'cell_capacity', 'module_capacity'],
            'wind': ['generation_capacity'],
            'battery': ['storage_capacity'],
            'hydrogen': ['electrolyzer_capacity', 'hydrogen_production'],
            'hydro': ['generation_capacity'],
            'biofuel': ['biofuel_capacity']
        }
        
        # Use default fields if specific type not found
        fields = metric_fields.get(project_type, 
                                  ['generation_capacity', 'storage_capacity'])
        
        # Check both camelCase and snake_case variations
        for field in fields:
            camel_case = ''.join(word.capitalize() if i > 0 else word 
                               for i, word in enumerate(field.split('_')))
            snake_case = field
            
            for col_name in [camel_case, snake_case]:
                if col_name in row and pd.notna(row[col_name]):
                    if col_name not in self.category_metrics[project_type]:
                        self.category_metrics[project_type][col_name] = []
                    
                    self.category_metrics[project_type][col_name].append(float(row[col_name]))
    
    def get_training_results(self):
        """Get summarized training results for use in project detection"""
        results = {}
        
        for project_type, keywords in self.category_keywords.items():
            # Filter out common words and single-character words
            common_words = {'project', 'power', 'energy', 'plant', 'system', 'a', 'the', 'of', 'in', 'at'}
            filtered_keywords = [k for k in keywords if k not in common_words and len(k) > 1]
            
            # Get top phrases
            phrases = list(self.category_phrases.get(project_type, []))
            
            # Get metrics statistics
            metrics = self.category_metrics.get(project_type, {})
            
            results[project_type] = {
                'keywords': filtered_keywords,
                'phrases': phrases,
                'metrics': metrics
            }
        
        return results
    
    def enhance_scraper_detection(self, text, current_scores=None):
        """
        Use trained patterns to enhance project type detection in the scraper
        
        Args:
            text: The article text to analyze
            current_scores: Optional dict of current scores from regular detection
            
        Returns:
            Dict of enhanced scores for each project type
        """
        if current_scores is None:
            current_scores = {}
        
        enhanced_scores = current_scores.copy()
        text = text.lower()
        
        # Calculate keyword-based scores for each project type
        for project_type, keywords in self.category_keywords.items():
            # Skip if we don't have enough training data
            if len(keywords) < 3:
                continue
                
            score = 0.0
            matched_keywords = []
            
            # Check for keywords
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', text):
                    score += 0.1
                    matched_keywords.append(keyword)
            
            # Check for phrases which are more specific
            for phrase in self.category_phrases.get(project_type, []):
                if phrase in text:
                    score += 0.2
                    matched_keywords.append(phrase)
            
            # If we found matches, update score
            if score > 0:
                # Combine with existing score if any
                existing_score = enhanced_scores.get(project_type, 0.0)
                enhanced_scores[project_type] = min(0.95, existing_score + score)
                
                # Log matched keywords for diagnostic purposes
                logger.debug(f"Enhanced {project_type} score to {enhanced_scores[project_type]} "
                            f"based on keywords: {matched_keywords}")
        
        return enhanced_scores


# Utility function to find and process all Excel files
def train_from_all_excel_files():
    """Process all available Excel files for training"""
    trainer = ProjectTypeTrainer()
    
    excel_files = [f for f in os.listdir() if f.endswith('.xlsx') and 'renewable' in f]
    logger.info(f"Found {len(excel_files)} Excel files for training")
    
    for excel_file in excel_files:
        logger.info(f"Processing {excel_file}")
        trainer.process_excel_file(excel_file)
    
    # Return training results
    return trainer.get_training_results()


if __name__ == "__main__":
    # Process all Excel files when run directly
    results = train_from_all_excel_files()
    print("Training complete!")
    print(f"Categories trained: {list(results.keys())}")
    
    for category, data in results.items():
        print(f"\n{category.upper()} TRAINING RESULTS:")
        print(f"Keywords ({len(data['keywords'])}): {', '.join(data['keywords'][:10])}...")
        print(f"Phrases ({len(data['phrases'])}): {', '.join(data['phrases'][:5])}...")