import requests
from bs4 import BeautifulSoup
import logging
import re
import time
import trafilatura
from datetime import datetime
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

# Import diagnostic tracker for monitoring potential projects
try:
    from diagnostic_tracker import diagnostic_tracker
    DIAGNOSTIC_MODE = True
    logger.info("Diagnostic tracker enabled for monitoring potential projects")
except ImportError:
    DIAGNOSTIC_MODE = False
    logger.warning("Diagnostic tracker not available")

# Check if newspaper3k is available
try:
    from newspaper import Article
    USE_NEWSPAPER = True
    logger.info("Using newspaper3k for article extraction")
except ImportError:
    USE_NEWSPAPER = False
    logger.warning("newspaper3k not available, using fallback extraction method")

# Energy categories with keywords and capacity patterns
ENERGY_CATEGORIES = {
    "Solar": {
        "keywords": [
            "solar", "photovoltaic", "pv", "solar panel", "solar cell", "solar module",
            "solar manufacturing", "solar plant", "solar farm", "solar park"
        ],
        "capacity_patterns": [
            r"(\d+(?:\.\d+)?)\s*(?:gw|gigawatt|mw|megawatt)",
            r"(\d+(?:\.\d+)?)\s*(?:gw|mw)\s*solar",
            r"solar\s*(?:capacity|plant|farm)\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:gw|mw)"
        ]
    },
    "Battery": {
        "keywords": [
            "battery", "energy storage", "lithium-ion", "li-ion", "storage system", "bess",
            "battery manufacturing", "battery factory", "cell production", "gigafactory"
        ],
        "capacity_patterns": [
            r"(\d+(?:\.\d+)?)\s*(?:gwh|gw|mwh|mw)\s*(?:battery|storage)",
            r"storage\s*(?:capacity|system)\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:gwh|mwh)"
        ]
    },
    "Wind": {
        "keywords": [
            "wind energy", "wind power", "wind turbine", "windmill", "wind farm", "wind park",
            "wind manufacturing", "turbine manufacturing"
        ],
        "capacity_patterns": [
            r"(\d+(?:\.\d+)?)\s*(?:gw|mw)\s*wind",
            r"wind\s*(?:capacity|farm|park)\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:gw|mw)"
        ]
    },
    "Hydro": {
        "keywords": [
            "hydro power", "hydroelectric", "hydropower", "hydel", "water power",
            "hydro plant", "dam", "pumped storage"
        ],
        "capacity_patterns": [
            r"(\d+(?:\.\d+)?)\s*(?:gw|mw)\s*hydro",
            r"hydro\s*(?:capacity|plant|project)\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:gw|mw)"
        ]
    },
    "Green Hydrogen": {
        "keywords": [
            "green hydrogen", "renewable hydrogen", "clean hydrogen", "hydrogen plant",
            "electrolyzer", "electrolysis", "green ammonia"
        ],
        "capacity_patterns": [
            r"(\d+(?:\.\d+)?)\s*(?:mw|gw)\s*electrolyzer",
            r"hydrogen\s*(?:production|facility)\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:mw|gw|tonnes)"
        ]
    },
    "Biofuel": {
        "keywords": [
            "biofuel", "ethanol", "bioethanol", "biodiesel", "biogas", "biomethane",
            "cbg", "compressed biogas"
        ],
        "capacity_patterns": [
            r"(\d+(?:\.\d+)?)\s*(?:million|lakh)\s*(?:litres|liters)",
            r"biogas\s*(?:plant|facility)\s*(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:cbg|tonnes)"
        ]
    }
}

def fetch_news_from_source(source_url):
    """Fetch news articles from a source website"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(source_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        links = []
        
        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            if not href:
                continue
                
            # Convert relative URLs to absolute
            if href.startswith('/'):
                link = urljoin(source_url, href)
            elif href.startswith('http'):
                link = href
            else:
                continue
                
            # Filter out non-article links and problematic file types
            if any(excluded in link.lower() for excluded in [
                'javascript:', 'mailto:', '#', 'facebook.com', 'twitter.com', 
                'linkedin.com', 'instagram.com', 'youtube.com', '.pdf', '.doc', 
                '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.rar'
            ]):
                continue
                
            # Look for article indicators
            if any(indicator in link.lower() for indicator in [
                'article', 'news', 'story', '/20', 'renewable', 'solar', 'battery', 
                'energy', 'manufacturing', 'production'
            ]):
                links.append(link)
        
        links = list(set(links))  # Remove duplicates
        logger.info(f"Found {len(links)} potential article links at {source_url}")
        return links
        
    except Exception as e:
        logger.error(f"Error fetching from {source_url}: {str(e)}")
        return []

def extract_article_content(article_url):
    """Extract content from an article with timeout protection"""
    try:
        # Skip problematic file types and domains
        if any(ext in article_url.lower() for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx']):
            logger.warning(f"Skipping file download: {article_url}")
            return {'title': '', 'text': '', 'publish_date': None}
        
        if USE_NEWSPAPER:
            article = Article(article_url)
            article.download()
            article.parse()
            
            return {
                'title': article.title or '',
                'text': article.text or '',
                'publish_date': article.publish_date
            }
        else:
            # Fallback method using requests and BeautifulSoup with shorter timeout
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(article_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Skip if response is too large (likely a file)
            if len(response.content) > 5 * 1024 * 1024:  # 5MB limit
                logger.warning(f"Skipping large content: {article_url}")
                return {'title': '', 'text': '', 'publish_date': None}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title = ''
            title_tag = soup.find('h1') or soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
            
            # Extract content
            content = ''
            content_selectors = ['article', '.article-content', '.entry-content', '.post-content', '.content']
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    paragraphs = elements[0].find_all('p')
                    content = ' '.join([p.get_text(strip=True) for p in paragraphs])
                    break
            
            if not content:
                # Fallback: get all paragraphs
                paragraphs = soup.find_all('p')
                content = ' '.join([p.get_text(strip=True) for p in paragraphs])
            
            return {
                'title': title,
                'text': content,
                'publish_date': None
            }
            
    except Exception as e:
        logger.error(f"Error extracting content from {article_url}: {str(e)}")
        return {'title': '', 'text': '', 'publish_date': None}

def is_india_project(text):
    """Check if the article is about an Indian project"""
    if not text:
        return False
    
    text_lower = text.lower()
    india_indicators = [
        'india', 'indian', 'maharashtra', 'gujarat', 'rajasthan', 'karnataka',
        'tamil nadu', 'telangana', 'andhra pradesh', 'haryana', 'punjab',
        'madhya pradesh', 'uttar pradesh', 'bihar', 'west bengal', 'odisha',
        'jharkhand', 'chhattisgarh', 'kerala', 'goa', 'himachal pradesh',
        'uttarakhand', 'jammu and kashmir', 'ladakh', 'delhi', 'mumbai',
        'bangalore', 'chennai', 'hyderabad', 'pune', 'ahmedabad', 'surat',
        'mnre', 'ministry of new and renewable energy', 'make in india',
        'pli scheme', 'atmanirbhar bharat'
    ]
    
    for indicator in india_indicators:
        if indicator in text_lower:
            return True
    
    return False

def is_renewable_project(text):
    """Determine if the text is about a renewable energy project"""
    if not text:
        return False, None
    
    text_lower = text.lower()
    
    # Check for project indicators
    project_indicators = [
        'project', 'plant', 'facility', 'farm', 'park', 'installation',
        'development', 'construction', 'capacity', 'expansion', 'build',
        'investment', 'announce', 'plan', 'launch', 'commission'
    ]
    
    has_project = any(indicator in text_lower for indicator in project_indicators)
    if not has_project:
        return False, None
    
    # Check for renewable energy categories
    scores = {}
    for category, data in ENERGY_CATEGORIES.items():
        score = 0
        for keyword in data["keywords"]:
            if keyword in text_lower:
                score += 1
        
        # Check capacity patterns
        for pattern in data["capacity_patterns"]:
            if re.search(pattern, text_lower, re.IGNORECASE):
                score += 2
        
        if score > 0:
            scores[category] = score
    
    if scores:
        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]
        
        if best_score >= 1:  # Lower threshold for more detection
            return True, best_category
    
    return False, None

def is_pipeline_project(text):
    """Check if the project is in pipeline (announced or under construction)"""
    if not text:
        return True  # Default to pipeline if we can't determine
    
    text_lower = text.lower()
    
    # Strong completed project indicators (already operational)
    strong_completed_indicators = [
        'inaugurated', 'started operations', 'operational since',
        'has been running', 'already operational', 'currently operational',
        'is operational', 'became operational'
    ]
    
    # Check for strong completion indicators
    for indicator in strong_completed_indicators:
        if indicator in text_lower:
            return False
    
    # Check for future completion dates (these indicate pipeline projects)
    future_completion_patterns = [
        r'(?:complete|commission|operational)\s*(?:by|in)\s*(?:20[2-9][5-9])',
        r'(?:expected|planned)\s*(?:to be|completion|commissioning)',
        r'will be\s*(?:completed|commissioned|operational)',
        r'under\s*(?:construction|development)',
        r'announced|planned|proposed'
    ]
    
    import re
    for pattern in future_completion_patterns:
        if re.search(pattern, text_lower):
            return True
    
    # If we find words like "completed" or "commissioned" but with future context, it's still pipeline
    completion_words = ['completed', 'commissioned']
    for word in completion_words:
        if word in text_lower:
            # Check if it's in future context
            word_index = text_lower.find(word)
            context = text_lower[max(0, word_index-50):word_index+50]
            if any(future_word in context for future_word in ['by 20', 'in 20', 'expected', 'will be', 'to be']):
                return True
    
    # Default to pipeline project
    return True

def extract_project_data(article_url, content=None):
    """Extract project data from an article"""
    if content is None:
        content = extract_article_content(article_url)
    
    if not content or not content.get('text'):
        return None
    
    text = content['text']
    title = content.get('title', '')
    
    # Check if it's about India
    india_project = is_india_project(text)
    if not india_project:
        return None
    
    # Check if it's a renewable energy project
    is_renewable, project_type = is_renewable_project(text)
    if not is_renewable:
        # Track potential projects that might be renewable but didn't pass filters
        if DIAGNOSTIC_MODE and any(keyword in text.lower() for keyword in ['energy', 'power', 'solar', 'wind', 'battery', 'hydrogen', 'biofuel']):
            diagnostic_tracker.track_potential_project(
                article_url,
                title or "Unknown Title",
                text[:500],
                {'renewable_confidence': 0.2, 'project_type': project_type or 'Unknown'},
                "Failed renewable energy project detection"
            )
        return None
    
    # Check if it's a pipeline project
    pipeline_project = is_pipeline_project(text)
    if not pipeline_project:
        # Track projects that are renewable but not pipeline
        if DIAGNOSTIC_MODE:
            diagnostic_tracker.track_potential_project(
                article_url,
                title or "Unknown Title", 
                text[:500],
                {'renewable_confidence': 0.8, 'pipeline_confidence': 0.2, 'project_type': project_type},
                "Failed pipeline project detection - might be operational project"
            )
        return None
    
    # Extract project details
    project_data = {
        'type': project_type,
        'name': extract_project_name(text, title),
        'company': extract_company(text),
        'location': extract_location(text),
        'investment_usd': extract_investment(text),
        'expected_completion': extract_completion_date(text),
        'source': article_url,
        'status': 'Pipeline'
    }
    
    # Extract capacity based on project type
    if project_type == 'Solar':
        project_data['generation_capacity'] = extract_solar_capacity(text)
    elif project_type == 'Battery':
        project_data['storage_capacity'] = extract_battery_capacity(text)
    elif project_type == 'Wind':
        project_data['generation_capacity'] = extract_wind_capacity(text)
    elif project_type == 'Hydro':
        project_data['generation_capacity'] = extract_hydro_capacity(text)
    elif project_type == 'Green Hydrogen':
        project_data['electrolyzer_capacity'] = extract_hydrogen_capacity(text)
    elif project_type == 'Biofuel':
        project_data['biofuel_capacity'] = extract_biofuel_capacity(text)
    
    return project_data

def extract_project_name(content, title=None):
    """Extract project name from content or title"""
    if title:
        # Clean up the title
        title = re.sub(r'\s*-\s*.*$', '', title)  # Remove everything after dash
        title = re.sub(r'\s*\|\s*.*$', '', title)  # Remove everything after pipe
        return title[:100]  # Limit length
    
    # Try to extract from first few sentences
    sentences = content.split('.')[:3]
    for sentence in sentences:
        if any(word in sentence.lower() for word in ['project', 'plant', 'facility']):
            return sentence.strip()[:100]
    
    return "Renewable Energy Project"

def extract_solar_capacity(content):
    """Extract capacity information for solar projects"""
    patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:gw|gigawatt)',
        r'(\d+(?:\.\d+)?)\s*(?:mw|megawatt)',
        r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:gw|mw)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content.lower())
        if match:
            value = float(match.group(1).replace(',', ''))
            if 'gw' in match.group(0):
                return value
            else:  # MW
                return value / 1000  # Convert to GW
    
    return None

def extract_battery_capacity(content):
    """Extract capacity information for battery projects"""
    patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:gwh|gw)',
        r'(\d+(?:\.\d+)?)\s*(?:mwh|mw)',
        r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:gwh|mwh)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content.lower())
        if match:
            value = float(match.group(1).replace(',', ''))
            if 'gwh' in match.group(0) or 'gw' in match.group(0):
                return value
            else:  # MWh or MW
                return value / 1000  # Convert to GWh
    
    return None

def extract_wind_capacity(content):
    """Extract capacity information for wind projects"""
    return extract_solar_capacity(content)  # Same pattern

def extract_hydro_capacity(content):
    """Extract capacity information for hydro projects"""
    return extract_solar_capacity(content)  # Same pattern

def extract_hydrogen_capacity(content):
    """Extract capacity information for hydrogen projects"""
    patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:mw|megawatt)\s*electrolyzer',
        r'electrolyzer\s*(?:capacity\s*)?(?:of\s*)?(\d+(?:\.\d+)?)\s*(?:mw|megawatt)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content.lower())
        if match:
            return float(match.group(1))
    
    return None

def extract_biofuel_capacity(content):
    """Extract capacity information for biofuel projects"""
    patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:million|lakh)\s*(?:litres|liters)',
        r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:litres|liters)\s*per\s*(?:day|year)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content.lower())
        if match:
            value = float(match.group(1).replace(',', ''))
            if 'million' in match.group(0):
                return value
            elif 'lakh' in match.group(0):
                return value / 10  # Convert lakh to million
            else:
                return value / 1000000  # Convert to million
    
    return None

def extract_location(content):
    """Extract location information from text"""
    states = [
        'maharashtra', 'gujarat', 'rajasthan', 'karnataka', 'tamil nadu',
        'telangana', 'andhra pradesh', 'haryana', 'punjab', 'madhya pradesh',
        'uttar pradesh', 'bihar', 'west bengal', 'odisha', 'jharkhand',
        'chhattisgarh', 'kerala', 'goa', 'himachal pradesh', 'uttarakhand'
    ]
    
    content_lower = content.lower()
    for state in states:
        if state in content_lower:
            return state.title()
    
    return None

def extract_company(content):
    """Extract company name from text"""
    # Common patterns for company names
    patterns = [
        r'([A-Z][a-zA-Z\s&]+(?:Ltd|Limited|Corp|Corporation|Inc|Pvt|Private))',
        r'([A-Z][a-zA-Z\s]+(?:Energy|Power|Solar|Industries|Technologies))',
        r'(Adani|Reliance|Tata|NTPC|BHEL|Mahindra|Suzlon|Waaree)[a-zA-Z\s]*'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1).strip()
    
    return None

def extract_investment(content):
    """Extract investment information"""
    patterns = [
        r'(?:investment|invest|worth|cost)\s*(?:of\s*)?(?:rs\.?\s*)?(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:crore|billion|million)',
        r'(?:usd|us\$|\$)\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:billion|million)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content.lower())
        if match:
            value = float(match.group(1).replace(',', ''))
            if 'crore' in match.group(0):
                return value * 10  # Convert crore to USD million (rough)
            elif 'billion' in match.group(0):
                return value * 1000  # Convert to million
            else:
                return value
    
    return None

def extract_completion_date(content):
    """Extract expected completion date"""
    patterns = [
        r'(?:by|in|during)\s*(\d{4})',
        r'(?:complete|commission|operational)\s*(?:by|in)\s*(\d{4})',
        r'(\d{4})\s*(?:completion|commissioning)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content.lower())
        if match:
            year = match.group(1)
            if 2024 <= int(year) <= 2035:  # Reasonable range
                return year
    
    return None