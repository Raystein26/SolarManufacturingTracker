import re
import time
import logging
import urllib.parse
import requests
import json
import nltk
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import trafilatura

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

# Energy category definitions
ENERGY_CATEGORIES = {
    "Solar": {
        "keywords": [
            "solar", "photovoltaic", "pv", "solar panel", "solar cell", "solar module",
            "solar power", "solar energy", "solar plant", "solar farm", "solar park",
            "rooftop solar", "floating solar", "solar manufacturing"
        ],
        "capacity_patterns": [
            r'(\d+(?:\.\d+)?)\s*GW\s*(?:of)?\s*(?:solar|pv)',
            r'(\d+(?:\.\d+)?)\s*MW\s*(?:of)?\s*(?:solar|pv)'
        ],
        "capacity_field": "generation_capacity",
        "capacity_unit": "GW"
    },
    
    "Wind": {
        "keywords": [
            "wind", "wind turbine", "wind farm", "wind park", "wind energy", "wind power",
            "onshore wind", "offshore wind", "windmill", "wind generation"
        ],
        "capacity_patterns": [
            r'(\d+(?:\.\d+)?)\s*GW\s*(?:of)?\s*(?:wind)',
            r'(\d+(?:\.\d+)?)\s*MW\s*(?:of)?\s*(?:wind)'
        ],
        "capacity_field": "generation_capacity",
        "capacity_unit": "GW"
    },
    
    "Hydro": {
        "keywords": [
            "hydro", "hydroelectric", "hydropower", "pumped storage", "hydel", 
            "hydro dam", "water power", "small hydro", "mini hydro", "micro hydro"
        ],
        "capacity_patterns": [
            r'(\d+(?:\.\d+)?)\s*GW\s*(?:of)?\s*(?:hydro|hydroelectric|hydropower)',
            r'(\d+(?:\.\d+)?)\s*MW\s*(?:of)?\s*(?:hydro|hydroelectric|hydropower)'
        ],
        "capacity_field": "generation_capacity",
        "capacity_unit": "GW"
    },
    
    "Battery": {
        "keywords": [
            "battery", "energy storage", "lithium-ion", "li-ion", "storage system", "bess",
            "battery energy storage", "grid storage", "power storage", "energy storage system"
        ],
        "capacity_patterns": [
            r'(\d+(?:\.\d+)?)\s*GWh',
            r'(\d+(?:\.\d+)?)\s*MWh'
        ],
        "capacity_field": "storage_capacity",
        "capacity_unit": "GWh"
    },
    
    "GreenHydrogen": {
        "keywords": [
            "green hydrogen", "renewable hydrogen", "clean hydrogen", "electrolyzer",
            "electrolysis", "hydrogen production", "h2", "hydrogen plant"
        ],
        "capacity_patterns": [
            r'(\d+(?:\.\d+)?)\s*GW\s*(?:of)?\s*(?:electrolyzer|electrolysis)',
            r'(\d+(?:\.\d+)?)\s*MW\s*(?:of)?\s*(?:electrolyzer|electrolysis)',
            r'(\d+(?:\.\d+)?)\s*(?:tons|tonnes)\s*(?:per day|per year|a day|a year|/day|/year)'
        ],
        "capacity_field": "electrolyzer_capacity",
        "capacity_unit": "MW"
    },
    
    "Biogas": {
        "keywords": [
            "biogas", "biomethane", "compressed biogas", "cbg", "bio-cng",
            "biomethanation", "organic waste to gas", "biogas plant"
        ],
        "capacity_patterns": [
            r'(\d+(?:\.\d+)?)\s*MMSCMD',
            r'(\d+(?:\.\d+)?)\s*(?:million cubic meters|mcm)'
        ],
        "capacity_field": "biofuel_capacity",
        "capacity_unit": "mmscmd"
    },
    
    "Ethanol": {
        "keywords": [
            "ethanol", "bioethanol", "biofuel", "ethanol blending", "distillery",
            "ethanol plant", "ethanol production", "e20", "flex fuel"
        ],
        "capacity_patterns": [
            r'(\d+(?:\.\d+)?)\s*(?:KLPD|kilo\s*litres\s*per\s*day)',
            r'(\d+(?:\.\d+)?)\s*(?:million\s*litres|million\s*liters)'
        ],
        "capacity_field": "biofuel_capacity",
        "capacity_unit": "ML"
    }
}

def fetch_news_from_source(source_url):
    """Fetch news articles from a source website"""
    try:
        logger.info(f"Fetching news from {source_url}")
        
        # Store article URLs
        article_urls = []
        
        # Make HTTP request
        response = requests.get(source_url, timeout=20)
        response.raise_for_status()
        
        # Parse HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all links
        for link in soup.find_all('a', href=True):
            url = link['href']
            
            # Skip non-article links
            if (not url or 
                url.startswith('#') or 
                url.startswith('javascript:') or
                url.startswith('mailto:') or
                'facebook.com' in url or
                'twitter.com' in url or
                'instagram.com' in url):
                continue
                
            # Make relative URLs absolute
            if not url.startswith(('http://', 'https://')):
                # Handle different relative URL formats
                if url.startswith('/'):
                    base_url = f"{urlparse(source_url).scheme}://{urlparse(source_url).netloc}"
                    url = base_url + url
                else:
                    url = source_url.rstrip('/') + '/' + url.lstrip('/')
                    
            # Filter for article-like URLs
            article_indicators = ['article', 'news', 'story', 'press-release', 'blog', 'post']
            if any(indicator in url.lower() for indicator in article_indicators):
                if url not in article_urls:
                    article_urls.append(url)
            
            # Also look for URLs with date patterns (common in news sites)
            date_pattern = r'\d{4}[/-]\d{2}[/-]\d{2}'
            if re.search(date_pattern, url):
                if url not in article_urls:
                    article_urls.append(url)
        
        logger.info(f"Found {len(article_urls)} potential article links at {source_url}")
        return article_urls
        
    except Exception as e:
        logger.error(f"Error fetching news from {source_url}: {str(e)}")
        return []

def extract_article_content(article_url):
    """Extract content from an article"""
    try:
        # Try using trafilatura first (usually gives the best results)
        downloaded = trafilatura.fetch_url(article_url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            if text and len(text) > 200:
                # Get more metadata with BeautifulSoup
                response = requests.get(article_url, timeout=15)
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract title
                title = soup.title.text if soup.title else ""
                
                # Extract published date if available
                published_date = None
                date_meta = soup.find('meta', attrs={'property': 'article:published_time'})
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
                    'url': article_url
                }
        
        # Fallback to basic BeautifulSoup extraction
        response = requests.get(article_url, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title = soup.title.text if soup.title else ""
        
        # Find main article content
        article_content = None
        
        # Look for common article containers
        for selector in ['article', 'main', '.article', '.content', '.post']:
            if '.' in selector:
                elements = soup.select(selector)
                if elements:
                    article_content = elements[0]
                    break
            else:
                element = soup.find(selector)
                if element:
                    article_content = element
                    break
        
        # If no specific container found, take the largest text block
        if not article_content:
            content_divs = soup.find_all('div')
            if content_divs:
                article_content = max(content_divs, key=lambda x: len(x.get_text(strip=True)))
        
        # Extract text from content
        if article_content:
            # Clean up - remove scripts, styles, etc.
            for unwanted in article_content.find_all(['script', 'style', 'nav', 'header', 'footer']):
                unwanted.decompose()
                
            text = article_content.get_text(separator=' ', strip=True)
            
            if text and len(text) > 200:
                return {
                    'title': title,
                    'text': text,
                    'published_date': None,
                    'url': article_url
                }
        
        return None
        
    except Exception as e:
        logger.error(f"Error extracting content from {article_url}: {str(e)}")
        return None

def is_india_project(text):
    """Check if the article is about an Indian project"""
    if not text:
        return False
    
    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    # Strong India indicators
    strong_indicators = [
        'india', 'indian', 'new delhi', 'goi', 'government of india', 
        'ministry of', 'make in india', 'niti aayog', 'pm modi', 'narendra modi'
    ]
    
    # Indian states and cities
    indian_locations = [
        'gujarat', 'maharashtra', 'tamil nadu', 'karnataka', 'rajasthan',
        'uttar pradesh', 'madhya pradesh', 'andhra pradesh', 'punjab', 'odisha',
        'telangana', 'kerala', 'haryana', 'delhi', 'west bengal', 'goa',
        'mumbai', 'delhi', 'chennai', 'bengaluru', 'hyderabad', 'pune', 'ahmedabad'
    ]
    
    # Indian companies
    indian_companies = [
        'tata', 'reliance', 'adani', 'mahindra', 'hero', 'larsen', 'toubro', 'l&t',
        'bhel', 'ntpc', 'ongc', 'gail', 'seci', 'nhai', 'iocl', 'bpcl', 'hpcl',
        'greenko', 'renew power', 'azure power', 'acme solar', 'sjvn', 'neepco',
        'nhpc', 'powergrid', 'suzlon', 'inox wind', 'indian oil', 'hindustan'
    ]
    
    # Check for strong indicators
    for indicator in strong_indicators:
        if indicator in text_lower:
            return True
    
    # Check for locations
    location_count = 0
    for location in indian_locations:
        if location in text_lower:
            location_count += 1
    
    # Check for companies
    company_count = 0
    for company in indian_companies:
        if company in text_lower:
            company_count += 1
    
    # Return True if we have at least one location indicator (more lenient)
    return (location_count >= 1 or company_count >= 1)

def is_renewable_project(text):
    """Determine if the text is about a renewable energy project"""
    if not text:
        logger.debug("No text provided to renewable project check")
        return False, None
    
    text_lower = text.lower()
    
    # Check for project keywords
    project_indicators = [
        'project', 'plant', 'facility', 'farm', 'park', 'installation',
        'development', 'construction', 'capacity', 'expansion', 'build',
        'investment', 'announce', 'plan', 'launch', 'commission'
    ]
    
    has_project = False
    for indicator in project_indicators:
        if indicator in text_lower:
            has_project = True
            logger.debug(f"Found project indicator: {indicator}")
            break
    
    if not has_project:
        logger.debug("No project indicators found in text")
        return False, None
    
    # Check for each energy category
    scores = {}
    logger.debug("Checking for renewable energy categories")
    for category, data in ENERGY_CATEGORIES.items():
        score = 0
        matched_keywords = []
        
        for keyword in data["keywords"]:
            if keyword in text_lower:
                # Exact matches get more weight
                if f" {keyword} " in f" {text_lower} ":
                    score += 2
                    matched_keywords.append(f"{keyword} (exact)")
                else:
                    score += 1
                    matched_keywords.append(keyword)
                    
        # Check for capacity patterns (give bonus points)
        for pattern in data["capacity_patterns"]:
            pattern_match = re.search(pattern, text_lower)
            if pattern_match:
                score += 3
                matched_keywords.append(f"capacity pattern: {pattern_match.group(0)}")
                
        if score > 0:
            scores[category] = score
            logger.debug(f"Category {category} score: {score} - matched: {', '.join(matched_keywords)}")
    
    # Find the highest scoring category
    if scores:
        best_category = max(scores.items(), key=lambda x: x[1])
        logger.debug(f"Best category: {best_category[0]} with score {best_category[1]}")
        
        # Minimum threshold to consider it as a renewable project (reduced from 2 to 1)
        if best_category[1] >= 1:
            logger.info(f"Renewable project detected! Category: {best_category[0]}, Score: {best_category[1]}")
            return True, best_category[0]
        else:
            logger.debug(f"Score too low: {best_category[1]} (minimum: 1)")
    else:
        logger.debug("No renewable energy categories detected")
    
    return False, None

def is_pipeline_project(text):
    """Check if the project is in pipeline (announced or under construction)"""
    if not text:
        return False
    
    text_lower = text.lower()
    
    # Pipeline status indicators
    pipeline_indicators = [
        'announced', 'plan', 'proposed', 'will build', 'to build', 
        'setting up', 'under construction', 'agreement signed', 'mou signed', 
        'to invest', 'to be commissioned', 'upcoming', 'future'
    ]
    
    # Completed project indicators (negative signals)
    completed_indicators = [
        'inaugurated', 'commissioned', 'started operations', 'operational since',
        'opened', 'completed in', 'was completed', 'has been running'
    ]
    
    # Check for pipeline indicators
    pipeline_match = False
    for indicator in pipeline_indicators:
        if indicator in text_lower:
            pipeline_match = True
            break
    
    # Check for completed indicators (negative)
    completed_match = False
    for indicator in completed_indicators:
        if indicator in text_lower:
            completed_match = True
            break
    
    # More lenient: accept if no completion indicators found, even without explicit pipeline keywords
    # This allows more projects through while still filtering out obviously completed ones
    return not completed_match

def extract_capacity(text, category):
    """Extract capacity information based on category patterns"""
    if not text or category not in ENERGY_CATEGORIES:
        return 0
    
    text_lower = text.lower()
    patterns = ENERGY_CATEGORIES[category]["capacity_patterns"]
    capacity_unit = ENERGY_CATEGORIES[category]["capacity_unit"]
    
    for pattern in patterns:
        matches = re.findall(pattern, text_lower)
        if matches:
            capacity = float(matches[0])
            
            # Convert MW to GW if needed for Solar, Wind, Hydro
            if "MW" in pattern and capacity_unit == "GW":
                capacity /= 1000
                
            # Convert MWh to GWh if needed for Battery
            if "MWh" in pattern and capacity_unit == "GWh":
                capacity /= 1000
                
            return capacity
    
    return 0

def extract_location(text):
    """Extract location information from text"""
    if not text:
        return "NA", "NA"
    
    # Indian states with normalized capitalization
    indian_states = {
        "andhra pradesh": "Andhra Pradesh",
        "arunachal pradesh": "Arunachal Pradesh",
        "assam": "Assam",
        "bihar": "Bihar",
        "chhattisgarh": "Chhattisgarh",
        "goa": "Goa",
        "gujarat": "Gujarat",
        "haryana": "Haryana",
        "himachal pradesh": "Himachal Pradesh",
        "jharkhand": "Jharkhand",
        "karnataka": "Karnataka",
        "kerala": "Kerala",
        "madhya pradesh": "Madhya Pradesh",
        "maharashtra": "Maharashtra", 
        "manipur": "Manipur",
        "meghalaya": "Meghalaya",
        "mizoram": "Mizoram",
        "nagaland": "Nagaland",
        "odisha": "Odisha",
        "punjab": "Punjab",
        "rajasthan": "Rajasthan",
        "sikkim": "Sikkim",
        "tamil nadu": "Tamil Nadu",
        "telangana": "Telangana",
        "tripura": "Tripura",
        "uttar pradesh": "Uttar Pradesh",
        "uttarakhand": "Uttarakhand",
        "west bengal": "West Bengal"
    }
    
    text_lower = text.lower()
    state = "NA"
    location = "NA"
    
    # Find state mentions
    for state_name_lower, state_name_proper in indian_states.items():
        if state_name_lower in text_lower:
            state = state_name_proper
            
            # Try to find a more specific location near the state mention
            state_index = text_lower.find(state_name_lower)
            if state_index > 0:
                # Search for location patterns around the state mention
                context = text_lower[max(0, state_index-100):min(len(text_lower), state_index+100)]
                
                location_patterns = [
                    rf'in\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\s*,?\s*{state_name_lower}',
                    rf'at\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+in\s+{state_name_lower}',
                    rf'near\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+in\s+{state_name_lower}'
                ]
                
                for pattern in location_patterns:
                    location_matches = re.findall(pattern, context)
                    if location_matches:
                        # Proper case for the location
                        location = location_matches[0].title()
                        break
            
            break
    
    return state, location

def extract_company(text):
    """Extract company name from text"""
    if not text:
        return "NA"
    
    # Company name patterns
    company_patterns = [
        r'([A-Z][a-z]*(?:\s+[A-Z][a-z]*){1,4}\s+(?:Limited|Ltd|Power|Energy|Renewables|Green|Solar|Wind|Hydro))',
        r'([A-Z][a-z]*(?:\s+[A-Z][a-z]*){0,2}\s+(?:&\s+Co))',
        r'((?:Tata|Reliance|Adani|NTPC|NHPC|SJVN|SECI|ReNew|Greenko|Azure|Inox|Suzlon|Hero|ACME|L&T|Larsen\s+&\s+Toubro)\s+[A-Za-z\s]{0,20}(?:Power|Energy|Green|Renewables|Solar|Electric)?)'
    ]
    
    for pattern in company_patterns:
        matches = re.findall(pattern, text)
        if matches:
            return matches[0].strip()
    
    return "NA"

def extract_investment(text):
    """Extract investment information"""
    if not text:
        return 0, 0
    
    text_lower = text.lower()
    
    # USD investment patterns
    usd_patterns = [
        r'(?:invest|investment of|funding of|cost of)\s*\$\s*(\d+(?:\.\d+)?)\s*(?:billion|bn)',
        r'(?:invest|investment of|funding of|cost of)\s*\$\s*(\d+(?:\.\d+)?)\s*(?:million|mn)',
        r'(?:invest|investment of|funding of|cost of)\s*(?:USD|US\$)\s*(\d+(?:\.\d+)?)\s*(?:billion|bn)',
        r'(?:invest|investment of|funding of|cost of)\s*(?:USD|US\$)\s*(\d+(?:\.\d+)?)\s*(?:million|mn)'
    ]
    
    # INR investment patterns
    inr_patterns = [
        r'(?:invest|investment of|funding of|cost of)\s*Rs\.?\s*(\d+(?:\.\d+)?)\s*(?:crore)',
        r'(?:invest|investment of|funding of|cost of)\s*(?:INR)\s*(\d+(?:\.\d+)?)\s*(?:crore)',
        r'(?:invest|investment of|funding of|cost of)\s*Rs\.?\s*(\d+(?:\.\d+)?)\s*(?:lakh)',
        r'(?:invest|investment of|funding of|cost of)\s*Rs\.?\s*(\d+(?:\.\d+)?)\s*(?:billion|bn)'
    ]
    
    # Try USD patterns first
    for i, pattern in enumerate(usd_patterns):
        matches = re.findall(pattern, text_lower)
        if matches:
            amount = float(matches[0])
            
            # Convert based on unit
            if 'billion' in pattern or 'bn' in pattern:
                amount *= 1000  # Convert billion to million
            
            # Set USD value and calculate approximate INR
            usd_million = amount
            inr_billion = amount * 82.5 / 1000  # Convert USD million to INR billion
            
            return usd_million, inr_billion
    
    # Try INR patterns next
    for i, pattern in enumerate(inr_patterns):
        matches = re.findall(pattern, text_lower)
        if matches:
            amount = float(matches[0])
            
            # Convert based on unit
            if 'crore' in pattern:
                amount /= 100  # Convert crore to billion
            elif 'lakh' in pattern:
                amount /= 10000  # Convert lakh to billion
            
            # Set INR value and calculate approximate USD
            inr_billion = amount
            usd_million = amount * 1000 / 82.5  # Convert INR billion to USD million
            
            return usd_million, inr_billion
    
    return 0, 0

def extract_project_data(article_url, content=None):
    """Extract project data from an article"""
    try:
        # Get content if not provided
        if not content:
            logger.debug(f"No content provided, extracting from URL: {article_url}")
            content = extract_article_content(article_url)
        
        if not content or not content.get('text'):
            logger.warning(f"No content extracted from {article_url}")
            return None
        
        # Log the start of extraction process with article title
        logger.info(f"Processing article: {content.get('title', 'No Title')} | URL: {article_url}")
        logger.debug(f"Article text length: {len(content['text'])} characters")
        
        # Check if it's an India project with more logging
        india_project = is_india_project(content['text'])
        logger.info(f"India project check result: {india_project} for {article_url}")
        if not india_project:
            logger.info(f"Article rejected - Not an India project: {article_url[:100]}...")
            return None
        
        # Check if it's a renewable project - this is where our detection happens
        is_renewable, energy_category = is_renewable_project(content['text'])
        logger.info(f"Renewable project check result: {is_renewable}, Category: {energy_category} for {article_url}")
        if not is_renewable or not energy_category:
            logger.info(f"Article rejected - Not a renewable energy project: {article_url[:100]}...")
            return None
        
        # Check if it's a pipeline project with more lenient criteria
        pipeline_check = is_pipeline_project(content['text'])
        logger.info(f"Pipeline project check result: {pipeline_check} for {article_url}")
        # Make this check less strict - accept if unclear
        if not pipeline_check:
            logger.info(f"Article rejected - Not a pipeline project: {article_url[:100]}...")
            return None
        
        # If we got this far, we have a valid renewable energy project!
        logger.info(f"NEW PROJECT FOUND! Category: {energy_category}, URL: {article_url}")
        
        # Extract basic project data
        title = content.get('title', '')
        text = content.get('text', '')
        
        # Get company name
        company = extract_company(text)
        
        # Get state and location
        state, location = extract_location(text)
        
        # Get capacity based on energy category
        capacity_field = ENERGY_CATEGORIES[energy_category]["capacity_field"]
        capacity = extract_capacity(text, energy_category)
        
        # Get investment information
        investment_usd, investment_inr = extract_investment(text)
        
        # Get the current date for project data
        current_date = datetime.now()
        
        # Set up correct category type based on keywords in text
        text_lower = text.lower()
        category = "NA"
        
        if "manufacturing" in text_lower or "factory" in text_lower or "giga" in text_lower:
            category = "Manufacturing"
        elif "generation" in text_lower or "power plant" in text_lower or "farm" in text_lower:
            category = "Generation"
        elif "storage" in text_lower:
            category = "Storage"
        elif any(keyword in text_lower for keyword in ["production", "distillery", "plant"]):
            category = "Production"
        
        # Default to specialized category based on energy type
        if category == "NA":
            if energy_category in ["Solar", "Wind", "Hydro"]:
                category = "Generation"
            elif energy_category == "Battery":
                category = "Storage"
            elif energy_category in ["GreenHydrogen", "Biogas", "Ethanol"]:
                category = "Production"
        
        # Determine inputs and outputs based on energy category
        input_output = {
            "Solar": {"input": "Sunlight", "output": "Electricity"},
            "Wind": {"input": "Wind", "output": "Electricity"},
            "Hydro": {"input": "Water", "output": "Electricity"},
            "Battery": {"input": "Electricity", "output": "Stored Electricity"},
            "GreenHydrogen": {"input": "Water & Electricity", "output": "Hydrogen"},
            "Biogas": {"input": "Organic Waste", "output": "Biogas/Biomethane"},
            "Ethanol": {"input": "Biomass/Sugarcane", "output": "Ethanol Fuel"}
        }
        
        # Create project data dictionary with all necessary fields
        project_data = {
            "Type": energy_category,
            "Name": title[:200] if title else "Renewable Project",
            "Company": company,
            "Ownership": "Private",  # Default
            "PLI/Non-PLI": "Non PLI",  # Default
            "State": state,
            "Location": location,
            "Announcement Date": current_date.strftime("%Y-%m-%d"),
            "Category": category,
            "Input": input_output.get(energy_category, {}).get("input", "NA"),
            "Output": input_output.get(energy_category, {}).get("output", "NA"),
            
            # Initialize all capacity fields (will set the appropriate one below)
            "Generation Capacity": 0,
            "Storage Capacity": 0,
            "Cell Capacity": 0,
            "Module Capacity": 0,
            "Integration Capacity": 0,
            "Electrolyzer Capacity": 0,
            "Hydrogen Production": 0,
            "Biofuel Capacity": 0,
            "Feedstock Type": "NA",
            
            # Set the specific capacity field based on energy category
            capacity_field: capacity,
            
            # Status fields
            "Status": "Announced",  # Default
            "Land Acquisition": "Not Started",  # Default
            "Power Approval": "Not Started",  # Default
            "Environment Clearance": "Not Started",  # Default
            "ALMM Listing": "Not Listed",  # Default
            "Investment USD": investment_usd,
            "Investment INR": investment_inr,
            "Expected Completion": "Not Specified",  # Default
            "Source": article_url
        }
        
        # Try to extract expected completion date
        completion_patterns = [
            r'(?:expected|scheduled|planned)\s+(?:to|for)\s+(?:complete|commission|finish)\s+(?:by|in)\s+(?:the\s+)?(\w+\s+\d{4}|\d{4})',
            r'(?:expected|scheduled|planned)\s+completion\s+(?:date|time|by|in)\s+(?:the\s+)?(\w+\s+\d{4}|\d{4})',
            r'(?:will|to)\s+be\s+(?:completed|commissioned|operational|ready)\s+(?:by|in)\s+(?:the\s+)?(\w+\s+\d{4}|\d{4})'
        ]
        
        for pattern in completion_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                project_data["Expected Completion"] = matches[0]
                break
        
        return project_data
        
    except Exception as e:
        logger.error(f"Error extracting project data: {str(e)}")
        return None