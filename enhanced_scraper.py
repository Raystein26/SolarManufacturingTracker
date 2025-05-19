"""
Enhanced scraper with training-based category detection and NLP-based entity recognition 
for renewable energy projects. This module integrates spaCy for advanced entity extraction
and the training module for better detection of diverse energy types.
"""

import os
import logging
import re
from datetime import datetime
import newspaper
from newspaper import Article
import trafilatura
from bs4 import BeautifulSoup
import requests
from collections import defaultdict
import nltk

# Import the training module and NLP processor
from training_module import ProjectTypeTrainer
from nlp_processor import analyze_project_text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the trainer with all available Excel files
trainer = ProjectTypeTrainer()
training_results = None

def load_training_data():
    """Load training data from Excel files"""
    global training_results
    # Lazy load training data when first needed
    if training_results is None:
        logger.info("Loading training data from Excel files...")
        # Find all Excel files with renewable projects data
        excel_files = [f for f in os.listdir() if f.endswith('.xlsx') and 'renewable' in f]
        if not excel_files:
            logger.warning("No training Excel files found")
            return {}
            
        # Process the latest file (assuming filename contains date)
        latest_file = sorted(excel_files)[-1]
        logger.info(f"Using {latest_file} for training")
        
        # Process the file and get training results
        trainer.process_excel_file(latest_file)
        training_results = trainer.get_training_results()
        logger.info(f"Loaded training data for {len(training_results)} project types")
    
    return training_results

def fetch_news_from_source(source_url):
    """
    Fetch news articles from a source website with enhanced search
    Returns a list of article URLs
    """
    try:
        logger.info(f"Fetching news from {source_url}")
        
        # Create a newspaper Source object
        source = newspaper.build(source_url, memoize_articles=False)
        
        # Extract article URLs
        article_urls = []
        for article in source.articles:
            # Process the URL to ensure it's properly formatted
            url = article.url
            
            # Skip URLs that don't look like news articles
            if any(skip in url.lower() for skip in ['login', 'signin', 'subscribe', 'advertise']):
                continue
                
            # Skip PDF and other file downloads
            if any(ext in url.lower() for ext in ['.pdf', '.csv', '.xlsx', '.zip']):
                continue
            
            article_urls.append(url)
        
        logger.info(f"Found {len(article_urls)} potential article links at {source_url}")
        return article_urls
        
    except Exception as e:
        logger.error(f"Error fetching news from {source_url}: {e}")
        return []

def extract_article_content(article_url):
    """
    Extract content from an article using the best available method
    Returns the article content and title
    """
    content = None
    title = None
    
    # Try newspaper first for extraction
    try:
        article = Article(article_url)
        article.download()
        article.parse()
        
        title = article.title
        content = article.text
        
        # Return early if we have good content
        if content and len(content) > 200:
            return content, title
            
    except Exception as e:
        logger.error(f"Error extracting with newspaper: {e} on URL {article_url}")
    
    # If newspaper fails or returns too little content, try trafilatura
    if not content or len(content) < 200:
        try:
            downloaded = trafilatura.fetch_url(article_url)
            content = trafilatura.extract(downloaded)
            
            # If we have content but no title, try to extract it
            if content and not title:
                soup = BeautifulSoup(downloaded, 'html.parser')
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.text.strip()
                
        except Exception as e:
            logger.error(f"Error extracting with trafilatura: {e} on URL {article_url}")
    
    # If both methods fail, try alternative extraction with BeautifulSoup
    if not content or len(content) < 200:
        try:
            content, title = extract_article_content_alternative(article_url)
        except Exception as e:
            logger.error(f"Error extracting with alternative method: {e}")
    
    if not content:
        logger.warning(f"Failed to extract content from {article_url}")
        return None, None
        
    return content, title

def extract_article_content_alternative(article_url):
    """
    Alternative method to extract article content using trafilatura and BeautifulSoup
    Returns content and title
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(article_url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract title
    title = None
    title_tag = soup.find('title')
    if title_tag:
        title = title_tag.text.strip()
    
    # Try to find main content
    main_content = None
    
    # Look for article tags
    article_tag = soup.find('article')
    if article_tag:
        main_content = article_tag.get_text(separator=' ', strip=True)
    
    # Try common content div ids
    if not main_content or len(main_content) < 100:
        for content_id in ['content', 'main-content', 'article-content', 'story', 'post-content']:
            content_div = soup.find('div', id=lambda x: x and content_id in x.lower())
            if content_div:
                main_content = content_div.get_text(separator=' ', strip=True)
                break
    
    # If still no content, get text from all paragraphs
    if not main_content or len(main_content) < 100:
        paragraphs = soup.find_all('p')
        if paragraphs:
            main_content = ' '.join([p.get_text(strip=True) for p in paragraphs])
    
    return main_content, title

def preprocess_text(text):
    """
    Preprocess text for NLP analysis
    Returns cleaned and normalized text
    """
    if not text:
        return ""
        
    # Convert to lowercase
    text = text.lower()
    
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def is_india_project(text):
    """
    Check if the article is about an Indian project using enhanced NLP techniques
    Returns a score between 0 and 1 indicating confidence
    """
    if not text:
        return 0.0
        
    # Preprocess text
    text = preprocess_text(text)
    
    # Key markers for Indian projects
    india_markers = [
        'india', 'indian', 'bharat', 'new delhi', 'mumbai', 'bangalore', 
        'gujarat', 'rajasthan', 'tamil nadu', 'karnataka', 'andhra pradesh',
        'telangana', 'maharashtra', 'madhya pradesh', 'uttar pradesh',
        'pli scheme', 'mnre', 'seci', 'ntpc', 'ireda', 'eesl', 'ministry of power',
        'ministry of new and renewable energy', 'pm modi', 'prime minister modi'
    ]
    
    # Count matches
    matches = 0
    for marker in india_markers:
        if re.search(r'\b' + re.escape(marker) + r'\b', text):
            matches += 1
    
    # Calculate confidence score
    if matches >= 3:
        return 0.95  # Very confident if multiple markers
    elif matches >= 1:
        return 0.7   # Moderately confident
    else:
        return 0.1   # Low confidence
        
def is_pipeline_project(text):
    """
    Check if the project is in pipeline (announced or under construction)
    Returns a score between 0 and 1 indicating confidence
    """
    if not text:
        return 0.0
        
    # Preprocess text
    text = preprocess_text(text)
    
    # Pipeline markers
    pipeline_markers = [
        'announce', 'announced', 'announcing', 'will build', 'will develop', 'plans to',
        'proposed', 'proposal', 'upcoming', 'breaking ground', 'groundbreaking',
        'to be built', 'to be completed', 'in development', 'under development',
        'under construction', 'being built', 'beginning construction', 'start construction',
        'expected to be operational', 'will be commissioned', 'signed agreement',
        'signed mou', 'memorandum of understanding', 'awarded contract'
    ]
    
    # Negative markers (already completed)
    completed_markers = [
        'inaugurated', 'commissioned', 'completed', 'operational since', 
        'has been operating', 'in operation since', 'has been running'
    ]
    
    # Count pipeline matches
    pipeline_matches = 0
    for marker in pipeline_markers:
        if re.search(r'\b' + re.escape(marker) + r'\b', text):
            pipeline_matches += 1
    
    # Count completed matches
    completed_matches = 0
    for marker in completed_markers:
        if re.search(r'\b' + re.escape(marker) + r'\b', text):
            completed_matches += 1
    
    # Calculate score
    if pipeline_matches >= 2 and completed_matches == 0:
        return 0.9  # Very likely pipeline project
    elif pipeline_matches >= 1 and completed_matches <= 1:
        return 0.7  # Probable pipeline project
    elif pipeline_matches == completed_matches:
        return 0.4  # Unclear status
    else:
        return 0.1  # Likely completed or not a project announcement

def determine_project_type(text):
    """
    Determine renewable energy project type across expanded categories
    Returns a dictionary of scores for each type
    """
    if not text:
        return {}
        
    # Preprocess text
    text = preprocess_text(text)
    
    # Define keywords and patterns for each project type
    type_patterns = {
        'solar': [
            r'\bsolar\s+(?:power|energy|plant|project|farm|park|capacity|manufacturing|pv)',
            r'\bphotovoltaic\b', r'\bsolar\s+panel', r'\bsolar\s+module',
            r'\bpv\s+(?:project|plant|farm|park|manufacturing)'
        ],
        'battery': [
            r'\bbattery\s+(?:storage|plant|manufacturing|gigafactory|production)',
            r'\benergy\s+storage\b', r'\bess\b', r'\bbess\b',
            r'\blithium(?:-|\s+)ion', r'\bstorage\s+system', r'\bcell\s+manufacturing'
        ],
        'wind': [
            r'\bwind\s+(?:power|energy|farm|park|project|plant|turbine)',
            r'\boffshore\s+wind', r'\bonshore\s+wind', r'\bwind\s+capacity'
        ],
        'hydro': [
            r'\bhydro(?:power|electric)', r'\bhydel\b',
            r'\bmicro(?:-|\s+)hydro', r'\bsmall\s+hydro', r'\bpump(?:ed)?\s+storage'
        ],
        'hydrogen': [
            r'\bgreen\s+hydrogen', r'\bhydrogen\s+(?:production|plant|electrolyzer)',
            r'\belectroly[zs]er', r'\bh2\s+production'
        ],
        'biofuel': [
            r'\bbiofuel', r'\bbiogas', r'\bethanol\s+plant',
            r'\bbiodiesel', r'\bbiomass\s+(?:plant|energy|power)'
        ]
    }
    
    # Load training data to enhance detection
    training_data = load_training_data()
    
    # Track scores for each type and keyword matches for diagnostic purposes
    scores = {}
    match_details = defaultdict(list)
    
    # Calculate scores based on regex patterns
    for project_type, patterns in type_patterns.items():
        score = 0.0
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                score += 0.2 * min(len(matches), 3)  # Cap at 3 matches
                match_details[project_type].extend(matches[:3])
        
        # Normalize score to 0-1 range
        scores[project_type] = min(0.9, score)
    
    # Enhance scores using training data if available
    if training_data:
        enhanced_scores = trainer.enhance_scraper_detection(text, scores)
        
        # Compare original and enhanced scores for diagnostic purposes
        for project_type, score in enhanced_scores.items():
            if project_type not in scores or abs(scores[project_type] - score) > 0.1:
                logger.debug(f"Training enhanced {project_type} score: {scores.get(project_type, 0)} -> {score}")
        
        scores = enhanced_scores
    
    # Log details for diagnostic purposes
    logger.debug(f"Project type detection results: {scores}")
    logger.debug(f"Pattern matches: {dict(match_details)}")
    
    return scores

def extract_project_data(article_url, content=None):
    """
    Extract project data from an article using NLP-based entity recognition
    
    Args:
        article_url: URL of the article
        content: Optional pre-fetched content
        
    Returns:
        Dictionary with extracted project data or None if not a relevant project
    """
    # Get article content if not provided
    if not content:
        content, title = extract_article_content(article_url)
        if not content:
            return None
    else:
        # If content provided, try to extract title
        title = None
        try:
            article = Article(article_url)
            article.download()
            article.parse()
            title = article.title
        except:
            pass
            
    # Check if it's about an Indian project
    india_score = is_india_project(content)
    if india_score < 0.5:
        logger.info(f"Article rejected: Not about an Indian project (score: {india_score})")
        return None
    
    # Check if it's about a renewable energy project
    project_type_scores = determine_project_type(content)
    
    # Find the most likely project type
    max_score = 0
    project_type = None
    
    for type_name, score in project_type_scores.items():
        if score > max_score:
            max_score = score
            project_type = type_name
    
    # Reject if no strong project type identified
    if max_score < 0.4:
        logger.info(f"Article rejected: Not about a renewable energy project (max score: {max_score})")
        
        # Track potential misses for diagnostics
        try:
            from diagnostic_tracker import diagnostic_tracker
            diagnostic_tracker.track_potential_project(
                article_url,
                title or "Unknown Title",
                content[:500] + "...",
                project_type_scores,
                f"Low confidence in project type (max score: {max_score})"
            )
            logger.info(f"Tracked as potential miss in diagnostic tracker")
        except ImportError:
            logger.debug("Diagnostic tracker not available")
        
        return None
    
    # Check if it's a pipeline project
    pipeline_score = is_pipeline_project(content)
    if pipeline_score < 0.4:
        logger.info(f"Article rejected: Not about a pipeline project (score: {pipeline_score})")
        return None
    
    # Use NLP-based entity recognition to extract detailed information
    try:
        nlp_results = analyze_project_text(content, title)
        logger.info(f"NLP entity extraction complete for {article_url}")
    except Exception as e:
        logger.error(f"Error in NLP processing: {e}")
        nlp_results = {}
    
    # Extract project details based on identified type and NLP results
    project_data = {
        'type': project_type.capitalize() if project_type else 'Unknown',
        'name': (nlp_results.get('project_name') if nlp_results else None) or extract_project_name(content, title),
        'company': nlp_results.get('companies')[0] if nlp_results and nlp_results.get('companies') else extract_company(content),
        'location': nlp_results.get('location')[0] if nlp_results and nlp_results.get('location') else extract_location(content),
        'state': nlp_results.get('state') if nlp_results else None,
        'source': article_url,
        'announcement_date': datetime.now().strftime('%Y-%m-%d')
    }
    
    # Extract investment data if available from NLP
    if nlp_results and nlp_results.get('investment'):
        try:
            investment = nlp_results['investment']
            if investment.get('currency') == 'USD':
                project_data['investment_usd'] = investment.get('value', 0)
            else:  # INR
                project_data['investment_inr'] = investment.get('value', 0)
        except Exception as e:
            logger.error(f"Error processing investment data: {e}")
    
    # Extract completion date if available
    if nlp_results and nlp_results.get('completion_date'):
        try:
            project_data['expected_completion'] = nlp_results['completion_date']
        except Exception as e:
            logger.error(f"Error processing completion date: {e}")
            
    # Extract capacity information from NLP results if available
    if nlp_results and nlp_results.get('capacities') and len(nlp_results['capacities']) > 0:
        try:
            for capacity in nlp_results['capacities']:
                unit = capacity.get('unit', '').upper() if capacity.get('unit') else ''
                value = capacity.get('value', 0)
                
                # Determine which capacity field to update based on unit
                if 'GW' in unit or 'MW' in unit or 'KW' in unit:
                    if 'H' not in unit:  # Power capacity (not energy storage)
                        project_data['generation_capacity'] = value if 'GW' in unit else value/1000 if 'MW' in unit else value/1000000
                    else:  # Energy storage
                        project_data['storage_capacity'] = value if 'GWH' in unit else value/1000 if 'MWH' in unit else value/1000000
                
                # Special cases for different project types
                if project_type == 'hydrogen' and ('TON' in unit or 'TONNE' in unit):
                    project_data['hydrogen_production'] = value
                elif project_type == 'biofuel' and ('LITER' in unit or 'LITRE' in unit):
                    project_data['biofuel_capacity'] = value
        except Exception as e:
            logger.error(f"Error processing capacity data: {e}")
    
    # Extract capacity based on project type
    if project_type == 'solar':
        project_data.update(extract_solar_capacity(content))
    elif project_type == 'battery':
        project_data.update(extract_battery_capacity(content))
    elif project_type == 'wind':
        project_data.update(extract_wind_capacity(content))
    elif project_type == 'hydro':
        project_data.update(extract_hydro_capacity(content))
    elif project_type == 'hydrogen':
        project_data.update(extract_hydrogen_capacity(content))
    elif project_type == 'biofuel':
        project_data.update(extract_biofuel_capacity(content))
    
    # Extract investment information
    project_data.update(extract_investment(content))
    
    # Set expected completion
    project_data['expected_completion'] = extract_completion_date(content)
    
    logger.info(f"Extracted project data for {project_type} project: {project_data['name']}")
    return project_data

def extract_project_name(content, title=None):
    """Extract project name from content or title"""
    # Try to extract from title first
    if title:
        # Look for project name patterns in title
        project_patterns = [
            r'(?:announces|to set up|to build|developing|launches) ([^.]+)',
            r'([^.]+(?:solar|battery|energy|power|wind|hydro|hydrogen|biofuel|renewable)[^.]+)',
        ]
        
        for pattern in project_patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                # Limit length and clean up
                name = match.group(1).strip()
                # Truncate long names
                if len(name) > 80:
                    name = name[:77] + '...'
                return name
    
    # Extract from first few paragraphs of content as fallback
    if content:
        paragraphs = content.split('\n')
        for para in paragraphs[:3]:
            for phrase in ['project', 'plant', 'farm', 'facility']:
                match = re.search(fr'([^.]+{phrase}[^.]+)', para, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    # Truncate long names
                    if len(name) > 80:
                        name = name[:77] + '...'
                    return name
    
    # If no specific name found, use title or generic name
    if title:
        return title[:80]
    return "Unnamed Renewable Energy Project"

def extract_solar_capacity(content):
    """Extract capacity information for solar projects"""
    result = {'generation_capacity': None}
    
    # Patterns for solar capacity
    capacity_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:GW|gigawatt)',
        r'(\d+(?:\.\d+)?)\s*(?:MW|megawatt)',
        r'(\d+(?:\.\d+)?)[- ](?:GW|gigawatt)',
        r'(\d+(?:\.\d+)?)[- ](?:MW|megawatt)'
    ]
    
    for pattern in capacity_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            # Convert MW to GW if necessary
            if 'MW' in match.group(0) or 'megawatt' in match.group(0).lower():
                value /= 1000
            result['generation_capacity'] = value
            break
            
    # Check for manufacturing capacity
    manufacturing_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:GW|gigawatt)(?:[- ]capacity)?\s+(?:cell|module|manufacturing)',
        r'(?:cell|module|manufacturing)(?:[- ]capacity)?\s+of\s+(\d+(?:\.\d+)?)\s*(?:GW|gigawatt)'
    ]
    
    for pattern in manufacturing_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            if 'cell' in match.group(0).lower():
                result['cell_capacity'] = value
            elif 'module' in match.group(0).lower():
                result['module_capacity'] = value
            else:
                # Generic manufacturing capacity
                result['manufacturing_capacity'] = value
    
    return result

def extract_battery_capacity(content):
    """Extract capacity information for battery projects"""
    result = {'storage_capacity': None}
    
    # Patterns for battery capacity
    capacity_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:GWh|gigawatt[ -]hour)',
        r'(\d+(?:\.\d+)?)\s*(?:MWh|megawatt[ -]hour)',
        r'(\d+(?:\.\d+)?)[- ](?:GWh|gigawatt[ -]hour)',
        r'(\d+(?:\.\d+)?)[- ](?:MWh|megawatt[ -]hour)',
        r'storage capacity of (\d+(?:\.\d+)?)\s*(?:GWh|MWh|gigawatt[ -]hour|megawatt[ -]hour)'
    ]
    
    for pattern in capacity_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            # Convert MWh to GWh if necessary
            if 'MWh' in match.group(0) or 'megawatt' in match.group(0).lower():
                value /= 1000
            result['storage_capacity'] = value
            break
            
    # Check for manufacturing capacity
    manufacturing_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:GWh|gigawatt[ -]hour)(?:[- ]capacity)?\s+(?:cell|battery|manufacturing)',
        r'(?:cell|battery|manufacturing)(?:[- ]capacity)?\s+of\s+(\d+(?:\.\d+)?)\s*(?:GWh|gigawatt[ -]hour)'
    ]
    
    for pattern in manufacturing_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            if 'cell' in match.group(0).lower():
                result['cell_capacity'] = value
            else:
                # Generic manufacturing capacity
                result['manufacturing_capacity'] = value
    
    return result

def extract_wind_capacity(content):
    """Extract capacity information for wind projects"""
    result = {'generation_capacity': None}
    
    # Patterns for wind capacity
    capacity_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:GW|gigawatt)',
        r'(\d+(?:\.\d+)?)\s*(?:MW|megawatt)',
        r'(\d+(?:\.\d+)?)[- ](?:GW|gigawatt)',
        r'(\d+(?:\.\d+)?)[- ](?:MW|megawatt)',
        r'wind capacity of (\d+(?:\.\d+)?)\s*(?:GW|MW|gigawatt|megawatt)'
    ]
    
    for pattern in capacity_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            # Convert MW to GW if necessary
            if 'MW' in match.group(0) or 'megawatt' in match.group(0).lower():
                value /= 1000
            result['generation_capacity'] = value
            break
    
    return result

def extract_hydro_capacity(content):
    """Extract capacity information for hydro projects"""
    result = {'generation_capacity': None}
    
    # Patterns for hydro capacity
    capacity_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:GW|gigawatt)',
        r'(\d+(?:\.\d+)?)\s*(?:MW|megawatt)',
        r'hydro(?:power|electric)? capacity of (\d+(?:\.\d+)?)\s*(?:GW|MW|gigawatt|megawatt)'
    ]
    
    for pattern in capacity_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            # Convert MW to GW if necessary
            if 'MW' in match.group(0) or 'megawatt' in match.group(0).lower():
                value /= 1000
            result['generation_capacity'] = value
            break
    
    return result

def extract_hydrogen_capacity(content):
    """Extract capacity information for hydrogen projects"""
    result = {
        'electrolyzer_capacity': None,
        'hydrogen_production': None
    }
    
    # Patterns for electrolyzer capacity
    electrolyzer_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:GW|gigawatt)\s+electroly[zs]er',
        r'(\d+(?:\.\d+)?)\s*(?:MW|megawatt)\s+electroly[zs]er',
        r'electroly[zs]er capacity of (\d+(?:\.\d+)?)\s*(?:GW|MW|gigawatt|megawatt)'
    ]
    
    for pattern in electrolyzer_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            # Convert MW to GW if necessary
            if 'MW' in match.group(0) or 'megawatt' in match.group(0).lower():
                value /= 1000
            result['electrolyzer_capacity'] = value
            break
    
    # Patterns for hydrogen production
    production_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:tons|tonnes)\s+(?:per|a|\/)\s+(?:day|annum|year)',
        r'produce (\d+(?:\.\d+)?)\s*(?:tons|tonnes)',
        r'production of (\d+(?:\.\d+)?)\s*(?:tons|tonnes)'
    ]
    
    for pattern in production_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            # We store production in tons per day
            if 'annum' in match.group(0).lower() or 'year' in match.group(0).lower():
                value /= 365  # Convert annual to daily
            result['hydrogen_production'] = value
            break
    
    return result

def extract_biofuel_capacity(content):
    """Extract capacity information for biofuel projects"""
    result = {
        'biofuel_capacity': None,
        'feedstock_type': None
    }
    
    # Patterns for biofuel capacity
    capacity_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:million|thousand)?\s*(?:liters|litres|gallons)',
        r'produce (\d+(?:\.\d+)?)\s*(?:million|thousand)?\s*(?:liters|litres|gallons)',
        r'capacity of (\d+(?:\.\d+)?)\s*(?:million|thousand)?\s*(?:liters|litres|gallons)'
    ]
    
    for pattern in capacity_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            # Apply multiplier based on unit
            if 'million' in match.group(0).lower():
                value *= 1000000
            elif 'thousand' in match.group(0).lower():
                value *= 1000
            # Convert gallons to liters if necessary
            if 'gallons' in match.group(0).lower():
                value *= 3.78541  # Gallons to liters conversion
            
            result['biofuel_capacity'] = value
            break
    
    # Patterns for feedstock type
    feedstock_patterns = [
        r'(?:using|from|based on) (\w+) (?:as feedstock|as raw material)',
        r'feedstock\s+(?:is|from)\s+(\w+)',
        r'(\w+)(?:-|\s+)based biofuel'
    ]
    
    feedstock_types = [
        'sugarcane', 'corn', 'wheat', 'rice', 'sorghum', 'barley', 
        'agricultural waste', 'agricultural residue', 'crop residue',
        'forest residue', 'wood', 'waste', 'municipal waste', 'algae'
    ]
    
    # Direct mentions of feedstock
    for feedstock in feedstock_types:
        if re.search(r'\b' + re.escape(feedstock) + r'\b', content, re.IGNORECASE):
            result['feedstock_type'] = feedstock
            break
    
    # Indirect mentions using patterns
    if not result['feedstock_type']:
        for pattern in feedstock_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                result['feedstock_type'] = match.group(1).lower()
                break
    
    return result

def extract_location(content):
    """Extract location information from text"""
    indian_states = [
        'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
        'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
        'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
        'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
        'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal'
    ]
    
    # Dictionary to hold state and city/district
    location_data = {'state': None, 'location': None}
    
    # Extract state
    for state in indian_states:
        # Look for both full state name and common abbreviations
        state_pattern = r'\b' + re.escape(state) + r'\b'
        if re.search(state_pattern, content, re.IGNORECASE):
            location_data['state'] = state
            break
    
    # Extract more specific location if state is found
    if location_data['state']:
        # Find city or district near mention of state
        state_pattern = r'\b' + re.escape(location_data['state']) + r'\b'
        state_matches = list(re.finditer(state_pattern, content, re.IGNORECASE))
        
        for match in state_matches:
            # Look for location before and after state mention
            start_pos = max(0, match.start() - 100)
            end_pos = min(len(content), match.end() + 100)
            
            context = content[start_pos:end_pos]
            
            # Look for "in X" or "at X" patterns
            location_patterns = [
                r'in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
                r'at\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
                r'near\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
                r'district\s+(?:of\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
            ]
            
            for pattern in location_patterns:
                locations = re.findall(pattern, context)
                if locations:
                    for loc in locations:
                        # Skip if location is a state or common words
                        if loc not in indian_states and loc.lower() not in ['india', 'delhi']:
                            location_data['location'] = loc
                            break
            
            if location_data['location']:
                break
    
    # Return state or "India" as fallback if no specific state found
    if not location_data['state']:
        return "India"
    
    # Return combined location or just state if no specific location
    if location_data['location']:
        return f"{location_data['location']}, {location_data['state']}"
    else:
        return location_data['state']

def extract_company(content):
    """Extract company name from text"""
    # Common Indian renewable energy companies
    common_companies = [
        'Adani Green', 'ReNew Power', 'Tata Power', 'NTPC', 'Greenko',
        'JSW Energy', 'Azure Power', 'Hero Future Energies', 'Acme Solar',
        'Avaada Energy', 'Amplus Solar', 'Cleantech Solar', 'Sembcorp',
        'Suzlon', 'SB Energy', 'EDF Renewables', 'Inox Wind', 'SJVN',
        'Reliance Power', 'Torrent Power', 'SECI', 'CLP India', 'Mytrah Energy'
    ]
    
    # First look for exact matches of common companies
    for company in common_companies:
        if re.search(r'\b' + re.escape(company) + r'\b', content, re.IGNORECASE):
            return company
    
    # Try to extract using patterns
    company_patterns = [
        r'([A-Z][a-zA-Z\s]+(?:Energy|Power|Green|Renewables|Solar|Group|Limited|Ltd|Wind|Electric|Corporation|India|Pvt|Private))(?:\s+(?:Ltd|Limited|Inc|Pvt\.?|Private|Corp\.?|Corporation))?',
        r'([A-Z][a-zA-Z\s]+)\s+(?:has announced|is setting up|will build|plans to|announced)',
        r'(?:by|from)\s+([A-Z][a-zA-Z\s]+(?:Energy|Power|Green|Renewables|Solar|Group|Wind|Electric|Corporation|Ltd|Limited))'
    ]
    
    for pattern in company_patterns:
        matches = re.findall(pattern, content)
        if matches:
            # Clean up matches and filter out common non-company phrases
            filtered_matches = []
            
            for match in matches:
                if isinstance(match, tuple):  # Some regex groups return tuples
                    match = match[0]
                
                match = match.strip()
                
                # Skip if too short or contains common words
                if len(match) < 4:
                    continue
                
                if match.lower() in ['the', 'this', 'that', 'renewable', 'project']:
                    continue
                
                # Skip government entities which are often mentioned but not the developer
                if any(term in match.lower() for term in ['ministry', 'government of', 'government']):
                    continue
                
                filtered_matches.append(match)
            
            if filtered_matches:
                # Return the most frequently mentioned company
                from collections import Counter
                company_counter = Counter(filtered_matches)
                most_common = company_counter.most_common(1)[0][0]
                
                # Truncate long company names
                if len(most_common) > 50:
                    most_common = most_common[:47] + '...'
                    
                return most_common
    
    return "Unknown"

def extract_investment(content):
    """Extract investment information"""
    result = {
        'investment_usd': None,
        'investment_inr': None
    }
    
    # USD patterns
    usd_patterns = [
        r'(?:investment of|invest|invested|cost of|worth|valued at)\s+(?:USD|US\$|\$)\s*(\d+(?:\.\d+)?)\s*(?:billion|bn|million|mn|m)',
        r'(?:USD|US\$|\$)\s*(\d+(?:\.\d+)?)\s*(?:billion|bn|million|mn|m)\s+(?:investment|project|cost)',
        r'(\d+(?:\.\d+)?)\s*(?:billion|bn|million|mn|m)\s+(?:USD|US\$|\$)'
    ]
    
    for pattern in usd_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            
            # Apply multiplier based on unit
            if 'billion' in match.group(0).lower() or 'bn' in match.group(0).lower():
                value *= 1000  # Convert billion to million
            
            result['investment_usd'] = value
            break
    
    # INR patterns
    inr_patterns = [
        r'(?:investment of|invest|invested|cost of|worth|valued at)\s+(?:INR|Rs|₹)\s*(\d+(?:\.\d+)?)\s*(?:crore|cr|lakh|billion|bn|million|mn|m)',
        r'(?:INR|Rs|₹)\s*(\d+(?:\.\d+)?)\s*(?:crore|cr|lakh|billion|bn|million|mn|m)\s+(?:investment|project|cost)',
        r'(\d+(?:\.\d+)?)\s*(?:crore|cr|lakh|billion|bn|million|mn|m)\s+(?:INR|Rs|₹)'
    ]
    
    for pattern in inr_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            
            # Convert to billion INR
            if 'crore' in match.group(0).lower() or 'cr' in match.group(0).lower():
                value /= 100  # Convert crore to billion
            elif 'lakh' in match.group(0).lower():
                value /= 10000  # Convert lakh to billion
            elif 'million' in match.group(0).lower() or 'mn' in match.group(0).lower() or 'm' in match.group(0).lower():
                value /= 1000  # Convert million to billion
            
            result['investment_inr'] = value
            break
    
    # If we have USD but not INR, estimate INR (using approximate conversion)
    if result['investment_usd'] and not result['investment_inr']:
        result['investment_inr'] = result['investment_usd'] * 0.083  # Approximate USD to INR billion conversion
    
    # If we have INR but not USD, estimate USD
    if result['investment_inr'] and not result['investment_usd']:
        result['investment_usd'] = result['investment_inr'] * 12  # Approximate INR billion to USD million conversion
    
    return result

def extract_completion_date(content):
    """Extract expected completion date"""
    # Look for completion date patterns
    date_patterns = [
        r'(?:expected|scheduled|planned|slated) to (?:complete|be completed|commissioned|be commissioned|operational|be operational) by (\d{4})',
        r'(?:expected|scheduled|planned|slated) (?:completion|commissioning) (?:date|in|by) (\d{4})',
        r'(?:completion|commissioning) is (?:expected|scheduled|planned|slated) (?:in|by) (\d{4})',
        r'(?:expected|scheduled|planned|slated) to (?:complete|be completed|commissioned|be operational) in Q[1-4] (\d{4})',
        r'(?:expected|scheduled|planned|slated) to (?:complete|be completed|commissioned|be operational) in (?:January|February|March|April|May|June|July|August|September|October|November|December) (\d{4})'
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            year = match.group(1)
            
            # If we have quarter information
            quarter_match = re.search(r'Q([1-4]) ' + re.escape(year), match.group(0), re.IGNORECASE)
            if quarter_match:
                return f"Q{quarter_match.group(1)} {year}"
            
            # If we have month information
            month_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December) ' + re.escape(year), match.group(0), re.IGNORECASE)
            if month_match:
                return f"{month_match.group(1)} {year}"
            
            return year
    
    # If no specific year found, look for general timeframes
    timeframe_patterns = [
        r'(?:expected|scheduled|planned|slated) to (?:complete|be completed|commissioned|be operational) in (\d+) (?:years|months)',
        r'(?:expected|scheduled|planned|slated) (?:completion|commissioning) in (\d+) (?:years|months)',
        r'within (?:the next|next) (\d+) (?:years|months)'
    ]
    
    current_year = datetime.now().year
    
    for pattern in timeframe_patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            timeframe = int(match.group(1))
            if 'years' in match.group(0).lower():
                return str(current_year + timeframe)
            elif 'months' in match.group(0).lower():
                if timeframe >= 12:
                    return str(current_year + (timeframe // 12))
                else:
                    return str(current_year + 1)
    
    return "Unknown"


# Main function for testing
if __name__ == "__main__":
    # Test with a sample article URL
    sample_url = "https://www.example.com/sample-article"  # Replace with a real URL for testing
    
    # Set up logging for testing
    logging.basicConfig(level=logging.DEBUG)
    
    # Load training data
    training_data = load_training_data()
    print(f"Loaded training data for project types: {list(training_data.keys())}")
    
    # Test extraction (mock data for testing)
    test_content = """
    ReNew Power announced a new 500 MW solar power project in Gujarat.
    The project is expected to be completed by 2026 and will require an investment of USD 400 million.
    This will be one of the largest solar installations in western India.
    """
    
    results = extract_project_data(sample_url, test_content)
    if results:
        print("Extracted project data:")
        for key, value in results.items():
            print(f"  - {key}: {value}")
    else:
        print("No relevant project data extracted")