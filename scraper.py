import re
import time
import logging
import trafilatura
import requests
import newspaper
import nltk
import datetime
import urllib.parse
from urllib.parse import urlparse
from datetime import datetime
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('scraper')

# Initialize NLTK resources if needed
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)
    
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords', quiet=True)

def fetch_news_from_source(source_url):
    """Fetch news articles from a source website with enhanced search"""
    try:
        logger.info(f"Fetching news from {source_url}")
        
        # Initialize list to store article URLs
        article_urls = []
        
        # Attempt to fetch and parse the page
        response = requests.get(source_url, timeout=30)
        response.raise_for_status()
        
        # Parse with BeautifulSoup for more flexible extraction
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Method 1: Find all anchor tags with href attributes
        for a_tag in soup.find_all('a', href=True):
            url = a_tag['href']
            
            # Skip if not a valid URL or is a social media link
            if not url or url.startswith('#') or url.startswith('javascript:'):
                continue
                
            # Skip common non-article links
            if url.startswith('mailto:') or url.startswith('tel:') or \
               url.startswith('/cdn-cgi/') or 'facebook.com' in url or \
               'twitter.com' in url or 'instagram.com' in url:
                continue
                
            # Convert relative URLs to absolute
            if not url.startswith('http'):
                base_url = urlparse(source_url)
                if url.startswith('/'):
                    url = f"{base_url.scheme}://{base_url.netloc}{url}"
                else:
                    url = f"{source_url.rstrip('/')}/{url.lstrip('/')}"
            
            # Filter for article-like URLs
            if 'article' in url.lower() or 'news' in url.lower() or \
               'press-release' in url.lower() or 'story' in url.lower() or \
               'blog' in url.lower() or 'post' in url.lower():
                article_urls.append(url)
        
        # Method 2: Use newspaper library for additional extraction
        try:
            news_site = newspaper.build(source_url, memoize_articles=False, fetch_images=False)
            for article in news_site.articles:
                # Parse the URL to check domain
                article_domain = urlparse(article.url).netloc
                source_domain = urlparse(source_url).netloc
                
                # Only include articles from the same domain or subdomain
                if article_domain == source_domain or article_domain.endswith('.' + source_domain):
                    article_urls.append(article.url)
        except Exception as e:
            logger.warning(f"Newspaper extraction had issues: {str(e)}")
        
        # Additional method for more specialized websites using regex patterns
        try:
            # Look for common article URL patterns in the HTML
            article_patterns = [
                r'href=[\'"]([^\'"]*(?:article|story|news|report|update)[^\'"]*)[\'"]',
                r'href=[\'"]([^\'"]*\d{4}[/\-]\d{2}[/\-]\d{2}[^\'"]*)[\'"]',  # Date-based URLs
                r'href=[\'"]([^\'"]*(?:press-release|pressrelease)[^\'"]*)[\'"]'
            ]
            
            for pattern in article_patterns:
                matches = re.finditer(pattern, response.text)
                for match in matches:
                    url = match.group(1)
                    
                    # Convert relative URLs to absolute
                    if not url.startswith('http'):
                        base_url = urlparse(source_url)
                        if url.startswith('/'):
                            url = f"{base_url.scheme}://{base_url.netloc}{url}"
                        else:
                            url = f"{source_url.rstrip('/')}/{url.lstrip('/')}"
                            
                    article_urls.append(url)
        except Exception as e:
            logger.warning(f"Regex article extraction had issues: {str(e)}")
            
        # Remove duplicates while preserving order
        unique_urls = []
        for url in article_urls:
            if url not in unique_urls:
                unique_urls.append(url)
        
        logger.info(f"Found {len(unique_urls)} potential article links at {source_url}")
        return unique_urls
        
    except Exception as e:
        logger.error(f"Error fetching news from {source_url}: {str(e)}")
        return []

def extract_article_content(article_url):
    """Extract content from an article using the best available method"""
    try:
        # First attempt with newspaper library
        try:
            article = newspaper.Article(article_url)
            article.download()
            article.parse()
            
            if article.text and len(article.text) > 200:  # Basic validation
                logger.info("Using newspaper3k for article extraction")
                return {
                    'title': article.title,
                    'text': article.text,
                    'published_date': article.publish_date,
                    'meta': {
                        'keywords': article.meta_keywords,
                        'description': article.meta_description
                    }
                }
        except Exception as e:
            logger.error(f"Error extracting with newspaper: {str(e)} on URL {article_url}")
        
        # Try alternative method
        result = extract_article_content_alternative(article_url)
        if result:
            return result
            
        # If we reach here, extraction failed
        logger.warning(f"Failed to extract content from {article_url}")
        return None
        
    except Exception as e:
        logger.error(f"Error in extract_article_content for {article_url}: {str(e)}")
        return None

def extract_article_content_alternative(article_url):
    """Alternative method to extract article content using trafilatura and BeautifulSoup"""
    try:
        # First try trafilatura which is good for main text content
        downloaded = trafilatura.fetch_url(article_url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            if text and len(text) > 200:  # Basic validation
                
                # Now extract title with BeautifulSoup for more accuracy
                response = requests.get(article_url, timeout=15)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                title = soup.title.text if soup.title else ""
                
                # Extract meta description
                meta_desc = ""
                meta_tag = soup.find('meta', attrs={'name': 'description'}) or \
                           soup.find('meta', attrs={'property': 'og:description'})
                if meta_tag and 'content' in meta_tag.attrs:
                    meta_desc = meta_tag['content'].replace('\n', ' ').strip()
                
                # Extract published date
                published_date = None
                date_meta = soup.find('meta', attrs={'property': 'article:published_time'}) or \
                            soup.find('meta', attrs={'name': 'pubdate'}) or \
                            soup.find('meta', attrs={'name': 'publishdate'})
                                
                if date_meta and 'content' in date_meta.attrs:
                    try:
                        date_str = date_meta['content']
                        published_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    except:
                        pass
                        
                return {
                    'title': title,
                    'text': text,
                    'published_date': published_date,
                    'meta': {
                        'description': meta_desc
                    }
                }
        
        # If trafilatura fails, try BeautifulSoup with more advanced extraction
        response = requests.get(article_url, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get title
        title = soup.title.text if soup.title else ""
        
        # Try to find main content
        article_content = None
        
        # Method 1: Look for article or main content elements
        for tag_name in ['article', 'main', 'div.content', 'div.article', 'div.post']:
            if '.' in tag_name:
                tag, cls = tag_name.split('.')
                element = soup.find(tag, class_=cls)
            else:
                element = soup.find(tag_name)
            
            if element:
                article_content = element
                break
        
        # Method 2: Look for content by ID patterns
        if not article_content:
            for id_pattern in ['content', 'article', 'post', 'main', 'story']:
                element = soup.find(id=lambda x: x and id_pattern in x.lower())
                if element:
                    article_content = element
                    break
        
        # Method 3: Fallback to the largest div by text content
        if not article_content:
            divs = soup.find_all('div')
            if divs:
                article_content = max(divs, key=lambda x: len(x.get_text(strip=True)))
        
        if article_content:
            # Clean the content
            for tag in article_content.find_all(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()
                
            text = article_content.get_text(separator=' ', strip=True)
            
            if text and len(text) > 200:  # Basic validation
                return {
                    'title': title,
                    'text': text,
                    'published_date': None,
                    'meta': {}
                }
        
        return None
        
    except Exception as e:
        logger.error(f"Error extracting with alternative method: {str(e)}")
        return None

def preprocess_text(text):
    """Preprocess text for NLP analysis"""
    if not text:
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)
    
    return text.strip()

def calculate_similarity(text1, text2):
    """Calculate semantic similarity between two texts using TF-IDF and cosine similarity"""
    if not text1 or not text2:
        return 0
        
    try:
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        
        # Calculate cosine similarity
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return similarity
    except Exception as e:
        logger.error(f"Error calculating similarity: {str(e)}")
        return 0

def is_india_project(text):
    """Check if the article is about an Indian project using enhanced NLP techniques
    Returns a score between 0 and 1 indicating confidence"""
    if not text:
        return False
        
    # Preprocess text
    processed_text = preprocess_text(text)
    
    # Indian state and city names
    indian_locations = [
        'andhra pradesh', 'arunachal pradesh', 'assam', 'bihar', 'chhattisgarh',
        'goa', 'gujarat', 'haryana', 'himachal pradesh', 'jharkhand', 'karnataka',
        'kerala', 'madhya pradesh', 'maharashtra', 'manipur', 'meghalaya', 'mizoram',
        'nagaland', 'odisha', 'punjab', 'rajasthan', 'sikkim', 'tamil nadu', 'telangana',
        'tripura', 'uttar pradesh', 'uttarakhand', 'west bengal', 'andaman', 'nicobar',
        'chandigarh', 'dadra', 'nagar haveli', 'daman', 'diu', 'delhi', 'jammu', 'kashmir',
        'ladakh', 'lakshadweep', 'puducherry',
        'mumbai', 'delhi', 'bangalore', 'bengaluru', 'hyderabad', 'ahmedabad', 'chennai',
        'kolkata', 'surat', 'pune', 'jaipur', 'lucknow', 'kanpur', 'nagpur', 'visakhapatnam',
        'bhopal', 'patna', 'indore', 'thane', 'agra', 'coimbatore', 'vadodara', 'ghaziabad',
        'ludhiana', 'nashik'
    ]
    
    # Indian companies and organizations
    indian_entities = [
        'tata', 'reliance', 'adani', 'mahindra', 'bajaj', 'birla', 'infosys', 'wipro',
        'bhel', 'ntpc', 'ongc', 'ioc', 'sbi', 'larsen', 'toubro', 'l&t', 'gail', 'nhai',
        'nhpc', 'pgcil', 'hpcl', 'bpcl', 'sail', 'jindal', 'suzlon', 'greenko', 'renew power',
        'azure power', 'acme solar', 'hero', 'indian', 'bharat', 'hindustan'
    ]
    
    # Explicitly India-related terms
    india_terms = [
        'india', 'indian', 'ministry', 'government of india', 'goi', 'make in india', 
        'atmanirbhar', 'pli scheme', 'union minister', 'pm modi', 'narendra modi',
        'niti aayog', 'mnre', 'seci', 'ireda'
    ]
    
    # Count indicators
    location_count = sum(1 for location in indian_locations if location in processed_text)
    entity_count = sum(1 for entity in indian_entities if entity in processed_text)
    term_count = sum(1 for term in india_terms if term in processed_text)
    
    # Calculate score (with more weight on explicit India terms)
    total_indicators = len(indian_locations) + len(indian_entities) + len(india_terms) * 2
    weighted_count = location_count + entity_count + term_count * 2
    
    # Normalize to 0-1 range with a maximum weighted count cap
    max_expected_matches = 10  # Expecting at most this many matches in legitimate articles
    score = min(weighted_count, max_expected_matches) / max_expected_matches
    
    # Direct checks that provide high confidence
    if ' india ' in f' {processed_text} ' or ' indian ' in f' {processed_text} ':
        score = max(score, 0.6)  # Minimum score of 0.6 if 'india' or 'indian' is mentioned
    
    # Strong India indicators provide even higher confidence
    for strong_indicator in ['government of india', 'ministry of', 'indian renewable', 'in india']:
        if strong_indicator in processed_text:
            score = max(score, 0.8)
    
    logger.info(f"India project confidence score: {score:.2f}")
    return score > 0.4  # Threshold for considering it an Indian project

def is_pipeline_project(text):
    """Check if the project is in pipeline (announced or under construction)"""
    if not text:
        return False
        
    # Preprocess text
    processed_text = preprocess_text(text)
    
    # Pipeline status indicators
    pipeline_indicators = [
        'announced', 'announce', 'plan', 'planning', 'proposed', 'proposal',
        'will build', 'to build', 'to set up', 'setting up', 'will set up',
        'under construction', 'construction began', 'breaking ground',
        'agreement signed', 'mou signed', 'to invest', 'investing in',
        'to be commissioned', 'will be operational', 'slated for', 'planned',
        'in the works', 'development', 'upcoming', 'future', 'targets'
    ]
    
    # Project keywords
    project_indicators = [
        'project', 'plant', 'facility', 'factory', 'manufacturing', 'power plant',
        'farm', 'park', 'installation', 'gw', 'mw', 'gwh', 'mwh', 'capacity',
        'production', 'construction'
    ]
    
    # Deployed project indicators (negative signals)
    deployed_indicators = [
        'inaugurated', 'commissioned', 'started operations', 'operational since',
        'operating since', 'began production in', 'started producing',
        'fully operational', 'opened', 'has been running', 'completed in',
        'was completed'
    ]
    
    # Check for pipeline indicators
    is_pipeline = any(indicator in processed_text for indicator in pipeline_indicators)
    
    # Check for project mentions
    has_project_indicators = any(indicator in processed_text for indicator in project_indicators)
    
    # Check for deployed indicators (negative)
    is_not_deployed = not any(indicator in processed_text for indicator in deployed_indicators)
    
    # A project is in pipeline if it has pipeline indicators AND no deployment indicators
    # OR if it has project indicators AND no deployment indicators
    return (is_pipeline and is_not_deployed) or (has_project_indicators and is_not_deployed)


def determine_project_type(text):
    """Determine renewable energy project type across expanded categories"""
    if not text:
        return None
        
    text_lower = text.lower()
    
    # FIRST CHECK: Must be about renewables and energy
    renewable_terms = [
        "renewable energy", "clean energy", "green energy", "sustainable energy",
        "solar", "wind", "hydro", "battery", "energy storage", "green hydrogen",
        "biogas", "ethanol", "biofuel"
    ]
    
    energy_focus = False
    for term in renewable_terms:
        if term in text_lower:
            energy_focus = True
            break
    
    if not energy_focus:
        logger.info("Article lacks renewable energy focus")
        return None
    
    # SECOND CHECK: Must have capacity, production, or investment details
    capacity_patterns = [
        r'\d+(?:\.\d+)?\s*(?:GW|MW|GWh|MWh)', # Power capacity
        r'\d+(?:\.\d+)?\s*(?:TPD|tons per day)', # Production capacity (tons)
        r'\d+(?:\.\d+)?\s*(?:KLPD|KL|million litres)', # Ethanol capacity
        r'\d+(?:\.\d+)?\s*(?:MMSCMD)' # Gas capacity
    ]
    
    has_capacity = False
    for pattern in capacity_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            has_capacity = True
            break
            
    # Investment indicators
    investment_pattern = r'(?:invest|funding|investment).*?(?:Rs\.?|INR|\$|USD|crore|billion|million)\s*\d+'
    has_investment = re.search(investment_pattern, text, re.IGNORECASE) is not None
    
    if not (has_capacity or has_investment):
        logger.info("Article lacks specific capacity or investment details")
        return None
    
    # Define project categories and their keywords
    project_types = {
        "Solar": {
            "general": ["solar", "photovoltaic", "pv", "solar panel", "solar cell", "solar module"],
            "manufacturing": [
                "solar cell manufacturing", "solar module production", "pv manufacturing facility",
                "solar panel factory", "module manufacturing", "solar gigafactory", 
                "solar manufacturing capacity", "wafer production", "cell production line"
            ],
            "generation": [
                "solar plant", "solar power plant", "solar farm", "solar park", "solar generation",
                "utility-scale solar", "grid-connected solar", "solar power project"
            ]
        },
        
        "Battery": {
            "general": ["battery", "energy storage", "lithium-ion", "li-ion", "storage system", "bess"],
            "manufacturing": [
                "battery manufacturing", "battery factory", "cell production",
                "gigafactory", "battery cell facility", "energy storage manufacturing",
                "lithium-ion production", "battery manufacturing hub"
            ],
            "storage": [
                "grid storage", "battery storage project", "energy storage facility",
                "utility-scale storage", "power storage", "battery energy storage system"
            ]
        },
        
        "Wind": {
            "general": ["wind energy", "wind power", "wind turbine", "windmill"],
            "manufacturing": [
                "wind turbine manufacturing", "turbine factory", "wind equipment facility",
                "wind power component", "blade manufacturing", "nacelle production"
            ],
            "generation": [
                "wind farm", "wind park", "wind power plant", "offshore wind", "onshore wind", 
                "wind energy project", "wind generation facility"
            ]
        },
        
        "Hydro": {
            "general": ["hydro power", "hydroelectric", "hydropower", "hydel", "water power"],
            "generation": [
                "hydro plant", "hydroelectric plant", "hydro project", "dam", "pumped storage", 
                "small hydro", "micro hydro", "run-of-river", "hydroelectric facility"
            ]
        },
        
        "GreenHydrogen": {
            "general": ["green hydrogen", "renewable hydrogen", "clean hydrogen", "hydrogen plant"],
            "production": [
                "hydrogen production", "electrolyzer", "electrolysis", "green ammonia",
                "hydrogen facility", "hydrogen generation", "h2 production"
            ]
        },
        
        "Biogas": {
            "general": ["biogas", "biomethane", "compressed biogas", "cbg", "bio-cng"],
            "production": [
                "biogas plant", "anaerobic digester", "biogas production", "organic waste to gas",
                "biomethane facility", "biogas generation", "biogas upgrading"
            ]
        },
        
        "Ethanol": {
            "general": ["ethanol", "bioethanol", "biofuel", "ethanol blending"],
            "production": [
                "ethanol plant", "distillery", "ethanol production facility", "biofuel plant",
                "bioethanol facility", "ethanol manufacturing"
            ]
        }
    }
    
    # Calculate scores for each project type
    type_scores = {}
    for energy_type, categories in project_types.items():
        score = 0
        
        # Check general terms
        for term in categories["general"]:
            if f" {term} " in f" {text_lower} ":  # Exact match
                score += 2
            elif term in text_lower:  # Partial match
                score += 1
        
        # Check specific categories (manufacturing, generation, etc.)
        for category, terms in categories.items():
            if category == "general":
                continue  # Already processed
                
            for term in terms:
                if f" {term} " in f" {text_lower} ":  # Exact match
                    score += 3  # Higher weight for specialized terms
                elif term in text_lower:  # Partial match
                    score += 1
        
        type_scores[energy_type] = score
    
    # Find the highest scoring type
    highest_score = 0
    project_type = None
    for energy_type, score in type_scores.items():
        if score > highest_score:
            highest_score = score
            project_type = energy_type
    
    # THIRD CHECK: Scores must exceed minimum threshold
    MIN_SCORE_THRESHOLD = 2  # Lower threshold to be more lenient with detection
    
    if highest_score < MIN_SCORE_THRESHOLD:
        logger.info(f"Article doesn't have enough specific keywords (highest score: {highest_score})")
        return None
    
    # Make sure we're prioritizing renewable categories if scores are close
    # This helps ensure new categories get detected more easily
    renewable_priorities = {
        "Wind": 0.5,       # Add boost to Wind detection
        "Hydro": 0.5,      # Add boost to Hydro detection
        "GreenHydrogen": 1, # Add larger boost to Green Hydrogen
        "Biogas": 0.5,     # Add boost to Biogas detection
        "Ethanol": 0.5     # Add boost to Ethanol detection
    }
    
    # Apply priority boosts for renewable categories we want to promote
    for energy_type, boost in renewable_priorities.items():
        if energy_type in type_scores:
            type_scores[energy_type] += boost
            
    # Recalculate highest score after boosts
    highest_score = 0
    project_type = None
    for energy_type, score in type_scores.items():
        if score > highest_score:
            highest_score = score
            project_type = energy_type
    
    logger.info(f"Identified {project_type} project with score {highest_score}")
    return project_type


def extract_project_data(article_url, content=None):
    """Extract project data from an article"""
    try:
        if not content:
            content = extract_article_content(article_url)
        
        if not content or not content['text']:
            logger.warning(f"No content extracted from {article_url}")
            return None
            
        # Determine if it's an India project
        if not is_india_project(content['text']):
            logger.debug(f"Not an India project: {article_url}")
            return None
            
        # Determine if it's a pipeline project
        if not is_pipeline_project(content['text']):
            logger.debug(f"Not a pipeline project: {article_url}")
            return None
            
        # Determine project type
        project_type = determine_project_type(content['text'])
        if not project_type:
            logger.debug(f"Not a relevant project type: {article_url}")
            return None
            
        # Determine project category based on type and keywords in text
        text_lower = content['text'].lower()
        category = "NA"
        
        # Category detection keywords
        category_keywords = {
            "Manufacturing": ["manufacturing", "factory", "production", "facility", 
                             "giga", "fabrication", "manufacturing hub"],
            "Generation": ["generation", "power plant", "farm", "park", "power project", 
                          "electricity generation", "power facility"],
            "Storage": ["storage", "battery storage", "energy storage"],
            "Production": ["production", "plant", "distillery", "biogas plant"],
            "Distribution": ["distributed", "rooftop", "microgrid", "off-grid"]
        }
        
        # Determine category by keyword matches
        highest_score = 0
        for cat, keywords in category_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
            if score > highest_score:
                highest_score = score
                category = cat
                
        # Adjust category based on project type
        if project_type in ["GreenHydrogen", "Biogas", "Ethanol"]:
            category = "Production"
            
        # Define inputs and outputs based on project type
        input_output_map = {
            "Solar": {"input": "Sunlight", "output": "Electricity"},
            "Battery": {"input": "Electricity", "output": "Stored Electricity"},
            "Wind": {"input": "Wind", "output": "Electricity"},
            "Hydro": {"input": "Water", "output": "Electricity"},
            "GreenHydrogen": {"input": "Water & Electricity", "output": "Hydrogen"},
            "Biogas": {"input": "Organic Waste", "output": "Biogas/Biomethane"},
            "Ethanol": {"input": "Biomass/Sugarcane", "output": "Ethanol Fuel"}
        }
        
        # Basic data common to all project types
        data = {
            "Type": project_type,
            "Name": "",
            "Company": "",
            "Ownership": "Private",  # Default
            "PLI/Non-PLI": "Non PLI",  # Default
            "State": "NA",
            "Location": "NA",
            "Announcement Date": datetime.now().strftime("%d-%m-%Y"),
            "Category": category,
            "Input": input_output_map.get(project_type, {}).get("input", "NA"),
            "Output": input_output_map.get(project_type, {}).get("output", "NA"),
            
            # Initialize capacity fields based on project type
            "Generation Capacity": 0,
            "Storage Capacity": 0,
            "Cell Capacity": 0,
            "Module Capacity": 0,
            "Integration Capacity": 0,
            "Electrolyzer Capacity": 0,
            "Hydrogen Production": 0,
            "Biofuel Capacity": 0,
            "Feedstock Type": "NA",
            
            # Status fields
            "Status": "Announced",  # Default
            "Land Acquisition": "Not Started",  # Default
            "Power Approval": "Not Started",  # Default
            "Environment Clearance": "Not Started",  # Default
            "ALMM Listing": "Not Listed",  # Default
            "Investment USD": 0,
            "Investment INR": 0,
            "Expected Completion": "Not Specified",  # Default
        }
        
        # Extract project name - often in the title
        if content['title']:
            data["Name"] = content['title'][:100]  # Limit length
        
        # Extract company name
        company_patterns = [
            r'((?:[A-Z][a-z]*\s*){1,5}(?:Ltd|Limited|Corp|Corporation|Inc|Incorporated|Group|Energy|Power|Renewables|Solar|Technologies|Private Limited|Pvt\.\s*Ltd))',
            r'((?:[A-Z][a-z]*\s*){1,3}(?:&\s*Co))',
        ]
        
        for pattern in company_patterns:
            matches = re.findall(pattern, content['text'])
            if matches:
                # Take the first match as the company name
                data["Company"] = matches[0].strip()
                break
        
        # Extract state and location
        indian_states = [
            'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
            'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
            'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
            'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana',
            'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal'
        ]
        
        # Look for state mentions
        for state in indian_states:
            if state.lower() in content['text'].lower():
                data["State"] = state
                
                # Try to find a location near the state mention
                state_index = content['text'].lower().find(state.lower())
                if state_index > 0:
                    # Look for a location within 100 characters before or after the state
                    context = content['text'][max(0, state_index-100):min(len(content['text']), state_index+100)]
                    
                    # Look for "in {location}, {state}" or "at {location} in {state}" patterns
                    location_patterns = [
                        r'in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*,?\s*' + state,
                        r'at\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+in\s+' + state,
                        r'near\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+in\s+' + state
                    ]
                    
                    for pattern in location_patterns:
                        location_matches = re.findall(pattern, context, re.IGNORECASE)
                        if location_matches:
                            data["Location"] = location_matches[0]
                            break
                
                break
        
        # Extract capacity based on project type
        if project_type in ["Solar", "Wind", "Hydro"]:
            # Look for generation capacity (GW, MW)
            capacity_patterns = [
                r'(\d+(?:\.\d+)?)\s*GW', 
                r'(\d+(?:\.\d+)?)\s*MW'
            ]
            
            for pattern in capacity_patterns:
                matches = re.findall(pattern, content['text'], re.IGNORECASE)
                if matches:
                    capacity = float(matches[0])
                    # Convert MW to GW if needed
                    if 'MW' in pattern and not 'GW' in pattern:
                        capacity /= 1000
                    data["Generation Capacity"] = capacity
                    break
                    
        elif project_type == "Battery":
            # Look for storage capacity (GWh, MWh)
            capacity_patterns = [
                r'(\d+(?:\.\d+)?)\s*GWh', 
                r'(\d+(?:\.\d+)?)\s*MWh'
            ]
            
            for pattern in capacity_patterns:
                matches = re.findall(pattern, content['text'], re.IGNORECASE)
                if matches:
                    capacity = float(matches[0])
                    # Convert MWh to GWh if needed
                    if 'MWh' in pattern and not 'GWh' in pattern:
                        capacity /= 1000
                    data["Storage Capacity"] = capacity
                    break
                    
            # Also look for manufacturing capacity for batteries
            if "manufacturing" in content['text'].lower() or "factory" in content['text'].lower():
                cell_patterns = [
                    r'(\d+(?:\.\d+)?)\s*GWh\s*(?:cell|battery cell|cell production)',
                    r'(\d+(?:\.\d+)?)\s*MWh\s*(?:cell|battery cell|cell production)'
                ]
                
                for pattern in cell_patterns:
                    matches = re.findall(pattern, content['text'], re.IGNORECASE)
                    if matches:
                        capacity = float(matches[0])
                        # Convert MWh to GWh if needed
                        if 'MWh' in pattern and not 'GWh' in pattern:
                            capacity /= 1000
                        data["Cell Capacity"] = capacity
                        break
                        
        elif project_type == "GreenHydrogen":
            # Look for electrolyzer capacity (MW)
            electrolyzer_patterns = [
                r'(\d+(?:\.\d+)?)\s*GW\s*(?:electrolyzer|electrolysis)',
                r'(\d+(?:\.\d+)?)\s*MW\s*(?:electrolyzer|electrolysis)'
            ]
            
            for pattern in electrolyzer_patterns:
                matches = re.findall(pattern, content['text'], re.IGNORECASE)
                if matches:
                    capacity = float(matches[0])
                    # Convert GW to MW if needed
                    if 'GW' in pattern and not 'MW' in pattern:
                        capacity *= 1000
                    data["Electrolyzer Capacity"] = capacity
                    break
                    
            # Look for hydrogen production capacity (tons)
            production_patterns = [
                r'(\d+(?:\.\d+)?)\s*(?:tons|tonnes)\s*(?:per day|per year|a day|a year|/day|/year)',
                r'(\d+(?:\.\d+)?)\s*TPD',
                r'(\d+(?:\.\d+)?)\s*TPY'
            ]
            
            for pattern in production_patterns:
                matches = re.findall(pattern, content['text'], re.IGNORECASE)
                if matches:
                    data["Hydrogen Production"] = float(matches[0])
                    break
                    
        elif project_type in ["Biogas", "Ethanol"]:
            # For biogas, look for production capacity
            if project_type == "Biogas":
                capacity_patterns = [
                    r'(\d+(?:\.\d+)?)\s*MMSCMD',
                    r'(\d+(?:\.\d+)?)\s*(?:million cubic meters|million m3|MCM)'
                ]
                
                for pattern in capacity_patterns:
                    matches = re.findall(pattern, content['text'], re.IGNORECASE)
                    if matches:
                        data["Biofuel Capacity"] = float(matches[0])
                        break
                        
                # Look for feedstock type
                feedstock_patterns = [
                    r'(?:using|from|based on)\s+([a-z]+\s+(?:waste|residue|biomass))',
                    r'feedstock:?\s+([a-z]+\s+(?:waste|residue|biomass))'
                ]
                
                for pattern in feedstock_patterns:
                    matches = re.findall(pattern, content['text'], re.IGNORECASE)
                    if matches:
                        data["Feedstock Type"] = matches[0]
                        break
                        
            # For ethanol, look for production capacity
            elif project_type == "Ethanol":
                capacity_patterns = [
                    r'(\d+(?:\.\d+)?)\s*(?:KLPD|kilo\s*litres\s*per\s*day)',
                    r'(\d+(?:\.\d+)?)\s*(?:million\s*litres|million\s*liters)'
                ]
                
                for pattern in capacity_patterns:
                    matches = re.findall(pattern, content['text'], re.IGNORECASE)
                    if matches:
                        data["Biofuel Capacity"] = float(matches[0])
                        break
                        
                # Look for feedstock type
                feedstock_patterns = [
                    r'(?:using|from|based on)\s+([a-z]+\s+(?:molasses|bagasse|grain|maize|corn|sugarcane))',
                    r'feedstock:?\s+([a-z]+\s+(?:molasses|bagasse|grain|maize|corn|sugarcane))'
                ]
                
                for pattern in feedstock_patterns:
                    matches = re.findall(pattern, content['text'], re.IGNORECASE)
                    if matches:
                        data["Feedstock Type"] = matches[0]
                        break
        
        # Extract investment details (common for all types)
        investment_patterns = [
            # USD patterns
            r'(?:invest|investment of|funding of|capital of|cost of)\s*\$\s*(\d+(?:\.\d+)?)\s*(?:billion|bn)',
            r'(?:invest|investment of|funding of|capital of|cost of)\s*\$\s*(\d+(?:\.\d+)?)\s*(?:million|mn)',
            r'(?:invest|investment of|funding of|capital of|cost of)\s*(?:USD|US\$)\s*(\d+(?:\.\d+)?)\s*(?:billion|bn)',
            r'(?:invest|investment of|funding of|capital of|cost of)\s*(?:USD|US\$)\s*(\d+(?:\.\d+)?)\s*(?:million|mn)',
            
            # INR patterns
            r'(?:invest|investment of|funding of|capital of|cost of)\s*Rs\.?\s*(\d+(?:\.\d+)?)\s*(?:billion|bn)',
            r'(?:invest|investment of|funding of|capital of|cost of)\s*Rs\.?\s*(\d+(?:\.\d+)?)\s*(?:crore|cr)',
            r'(?:invest|investment of|funding of|capital of|cost of)\s*INR\s*(\d+(?:\.\d+)?)\s*(?:billion|bn)',
            r'(?:invest|investment of|funding of|capital of|cost of)\s*INR\s*(\d+(?:\.\d+)?)\s*(?:crore|cr)'
        ]
        
        for i, pattern in enumerate(investment_patterns):
            matches = re.findall(pattern, content['text'], re.IGNORECASE)
            if matches:
                amount = float(matches[0])
                
                # Process based on currency and unit
                if i < 4:  # USD patterns
                    # Convert to USD million
                    if 'billion' in pattern or 'bn' in pattern:
                        amount *= 1000  # Convert billion to million
                    data["Investment USD"] = amount
                    
                    # Estimate INR equivalent (rough conversion)
                    data["Investment INR"] = amount * 82.5 / 1000  # Convert USD million to INR billion
                else:  # INR patterns
                    # Convert to INR billion
                    if 'crore' in pattern or 'cr' in pattern:
                        amount /= 100  # Convert crore to billion
                    data["Investment INR"] = amount
                    
                    # Estimate USD equivalent (rough conversion)
                    data["Investment USD"] = amount * 1000 / 82.5  # Convert INR billion to USD million
                break
        
        # Extract expected completion date
        completion_patterns = [
            r'(?:expected|scheduled|planned|slated|due)\s+(?:to|for)\s+(?:complete|commission|finish|be ready|be completed|be commissioned)\s+(?:by|in)\s+(?:the\s+)?(\w+\s+\d{4}|\d{4})',
            r'(?:expected|scheduled|planned|slated|estimated)\s+(?:completion|commissioning)\s+(?:date|time|by|in)\s+(?:the\s+)?(\w+\s+\d{4}|\d{4})',
            r'(?:will|to)\s+be\s+(?:completed|commissioned|operational|ready)\s+(?:by|in)\s+(?:the\s+)?(\w+\s+\d{4}|\d{4})'
        ]
        
        for pattern in completion_patterns:
            matches = re.findall(pattern, content['text'], re.IGNORECASE)
            if matches:
                data["Expected Completion"] = matches[0]
                break
        
        # Extract project status if available
        status_patterns = {
            "Announced": [r'announced', r'plans to', r'will develop', r'proposed'],
            "Planning": [r'planning stage', r'in planning', r'planned for'],
            "Approved": [r'approved', r'received approval', r'got clearance'],
            "Land Acquisition": [r'acquiring land', r'land acquisition', r'secured land'],
            "Under Construction": [r'under construction', r'construction (?:has )?started', r'being constructed'],
            "Partially Commissioned": [r'partially commissioned', r'first phase', r'partially operational']
        }
        
        for status, patterns in status_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content['text'], re.IGNORECASE):
                    data["Status"] = status
                    break
            if data["Status"] != "Announced":  # Stop if we found a more specific status
                break
                
        # Clean up the name if needed
        if data["Name"] and len(data["Name"]) > 20 and not data["Company"]:
            # Try to extract company name from the title
            company_match = re.search(company_patterns[0], data["Name"])
            if company_match:
                data["Company"] = company_match.group(1)
        
        # Set source
        data["Source"] = article_url
        
        return data
        
    except Exception as e:
        logger.error(f"Error extracting project data: {str(e)}")
        return None