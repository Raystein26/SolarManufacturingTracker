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
            
            # Store original column names for later reference
            original_columns = df.columns.tolist()
            
            # Create a normalized column mapping for case-insensitive matching
            col_mapping = {col.lower(): col for col in df.columns}
            
            # Define possible column names for each required field (case-insensitive)
            field_alternatives = {
                'type': ['type', 'project_type', 'energy_type', 'renewable_type'],
                'name': ['name', 'project_name', 'project'],
                'company': ['company', 'organization', 'developer', 'owner'],
                'category': ['category', 'project_category', 'segment']
            }
            
            # Map actual column names to our standard names
            mapped_columns = {}
            for field, alternatives in field_alternatives.items():
                for alt in alternatives:
                    if alt.lower() in col_mapping:
                        mapped_columns[field] = col_mapping[alt.lower()]
                        logger.info(f"Mapped '{col_mapping[alt.lower()]}' to '{field}'")
                        break
            
            # Log which required fields are missing
            missing_fields = [field for field in field_alternatives.keys() 
                             if field not in mapped_columns]
            
            if missing_fields:
                logger.warning(f"Missing required columns: {missing_fields}")
                
                # Look for columns with similar names if still missing
                for field in missing_fields.copy():
                    for col in original_columns:
                        # Try partial matching
                        if field in col.lower():
                            mapped_columns[field] = col
                            missing_fields.remove(field)
                            logger.info(f"Using '{col}' for '{field}' based on partial match")
                            break
            
            # Create a new DataFrame with standardized column names
            std_df = pd.DataFrame()
            
            # Copy mapped columns to standardized DataFrame
            for std_name, orig_name in mapped_columns.items():
                std_df[std_name] = df[orig_name]
            
            # Check if we have project type column
            if 'type' not in mapped_columns:
                logger.error("Could not find a column for project type in Excel file")
                return
            
            # Extract patterns for each project type
            project_types = std_df['type'].unique()
            logger.info(f"Found {len(project_types)} project types: {project_types}")
            
            # Process each project type
            for project_type in project_types:
                if pd.isna(project_type):
                    continue
                
                # Handle numeric types by converting to string
                if isinstance(project_type, (int, float)):
                    project_type_str = str(project_type)
                    logger.info(f"Converting numeric type {project_type} to string")
                else:
                    project_type_str = project_type.strip().lower()
                
                # Filter for this project type, handling both string and numeric types
                if isinstance(project_type, (int, float)):
                    type_df = std_df[std_df['type'] == project_type]
                else:
                    try:
                        type_df = std_df[std_df['type'].str.lower() == project_type_str]
                    except AttributeError:
                        # Handle case where type column contains mixed types
                        type_df = std_df[std_df['type'].astype(str).str.lower() == project_type_str]
                
                logger.info(f"Processing {len(type_df)} examples for {project_type}")
                
                # Extract keywords from project names
                for _, row in type_df.iterrows():
                    # Use project_type_str for consistent key naming in dictionaries
                    self._extract_keywords(project_type_str, row)
                    self._extract_metrics(project_type_str, row)
            
            # After processing all examples, save the training data
            self.save_training_data()
            
        except Exception as e:
            logger.error(f"Error processing Excel file {excel_file}: {e}")
    
    def _extract_keywords(self, project_type, row):
        """Extract keywords from a project example"""
        # Make sure dictionary entries exist for this project type
        if project_type not in self.category_keywords:
            self.category_keywords[project_type] = set()
        if project_type not in self.category_phrases:
            self.category_phrases[project_type] = set()
            
        # Process name or alternatives
        name_fields = ['name', 'project_name', 'project']
        for field in name_fields:
            if field in row and pd.notna(row[field]):
                try:
                    name = str(row[field]).lower()
                    
                    # Add project name keywords
                    keywords = set(re.findall(r'\b\w+\b', name))
                    self.category_keywords[project_type].update(keywords)
                    
                    # Capture multi-word phrases that might be important
                    phrases = re.findall(r'\b\w+\s+\w+\b', name)
                    self.category_phrases[project_type].update(phrases)
                    
                    # Found a valid name field, no need to check others
                    break
                except Exception as e:
                    logger.warning(f"Error processing name field '{field}': {e}")
        
        # Process company name for additional context
        company_fields = ['company', 'organization', 'developer', 'owner']
        for field in company_fields:
            if field in row and pd.notna(row[field]):
                try:
                    company = str(row[field]).lower()
                    # Companies often specialize in specific renewable types
                    self.category_keywords[project_type].add(company)
                    break
                except Exception as e:
                    logger.warning(f"Error processing company field '{field}': {e}")
        
        # Process category for additional dimensions
        category_fields = ['category', 'project_category', 'segment', 'type']
        for field in category_fields:
            if field in row and pd.notna(row[field]) and field != 'type':
                try:
                    category = str(row[field]).lower()
                    self.category_keywords[project_type].add(category)
                    break
                except Exception as e:
                    logger.warning(f"Error processing category field '{field}': {e}")
    
    def _extract_metrics(self, project_type, row):
        """Extract metric patterns from a project example"""
        # Initialize metrics dictionary for this project type if it doesn't exist
        if project_type not in self.category_metrics:
            self.category_metrics[project_type] = {}
            
        # Different metrics for different project types with alternative field names
        metric_fields = {
            'solar': [
                'generation_capacity', 'capacity_mw', 'capacity', 'mw', 'size_mw',
                'cell_capacity', 'module_capacity', 'solar_capacity'
            ],
            'wind': [
                'generation_capacity', 'capacity_mw', 'capacity', 'mw', 'size_mw',
                'wind_capacity'
            ],
            'battery': [
                'storage_capacity', 'capacity_mwh', 'capacity', 'mwh', 'size_mwh',
                'battery_capacity'
            ],
            'hydrogen': [
                'electrolyzer_capacity', 'hydrogen_production', 'capacity_mw',
                'production_tons', 'tons_per_day', 'hydrogen_capacity'
            ],
            'hydro': [
                'generation_capacity', 'capacity_mw', 'capacity', 'mw', 'size_mw',
                'hydro_capacity'
            ],
            'biofuel': [
                'biofuel_capacity', 'capacity_ml', 'production_capacity',
                'million_liters', 'capacity', 'biofuel_production'
            ]
        }
        
        # Use default fields if specific type not found
        fields = metric_fields.get(project_type, 
                                  ['generation_capacity', 'capacity', 'storage_capacity'])
        
        # Also search for any column that contains keywords like 'capacity', 'mw', etc.
        capacity_keywords = ['capacity', 'mw', 'gwh', 'mwh', 'production', 'size']
        
        # Track if we found any metrics
        metrics_found = False
        
        # First try the known field names
        for field in fields:
            # Generate variations of column names: camelCase, snake_case, lowercase
            camel_case = ''.join(word.capitalize() if i > 0 else word 
                               for i, word in enumerate(field.split('_')))
            snake_case = field
            lowercase = field.lower().replace('_', '')
            
            for col_name in [field, camel_case, snake_case, lowercase]:
                if col_name in row and pd.notna(row[col_name]):
                    try:
                        if isinstance(row[col_name], (int, float)):
                            value = float(row[col_name])
                        else:
                            # Try to extract numeric value from string
                            value = float(re.search(r'[\d.]+', str(row[col_name])).group())
                            
                        if col_name not in self.category_metrics[project_type]:
                            self.category_metrics[project_type][col_name] = []
                        
                        self.category_metrics[project_type][col_name].append(value)
                        metrics_found = True
                        
                    except (ValueError, AttributeError, TypeError) as e:
                        logger.warning(f"Could not convert {col_name} value to float: {e}")
        
        # If no metrics found, try looking for columns with capacity keywords
        if not metrics_found:
            for col in row.index:
                col_lower = str(col).lower()
                if any(keyword in col_lower for keyword in capacity_keywords):
                    try:
                        if pd.notna(row[col]):
                            if isinstance(row[col], (int, float)):
                                value = float(row[col])
                            else:
                                # Try to extract numeric value from string
                                value = float(re.search(r'[\d.]+', str(row[col])).group())
                                
                            if col not in self.category_metrics[project_type]:
                                self.category_metrics[project_type][col] = []
                            
                            self.category_metrics[project_type][col].append(value)
                            
                    except (ValueError, AttributeError, TypeError) as e:
                        logger.debug(f"Could not extract metric from {col}: {e}")
            
    
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