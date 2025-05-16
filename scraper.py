import requests
from bs4 import BeautifulSoup
import logging
import re
import time
import trafilatura
from datetime import datetime
from urllib.parse import urljoin, urlparse
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# Check if newspaper3k is available
try:
    from newspaper import Article
    USE_NEWSPAPER = True
    logger.info("Using newspaper3k for article extraction")
except ImportError:
    USE_NEWSPAPER = False
    logger.warning("newspaper3k not available, using fallback extraction method")


# Keywords to track
SOLAR_KEYWORDS = [
    "solar module", "solar manufacturing", "solar cell", "pv manufacturing", 
    "photovoltaic production", "solar facility", "module plant", "solar panel factory",
    "solar capacity", "pv module", "solar factory", "solar panel production",
    "solar manufacturing plant", "cell production", "gw solar", "polysilicon",
    "wafer production", "ingot production", "solar manufacturing hub"
]

BATTERY_KEYWORDS = [
    "battery manufacturing", "battery cell", "battery module", 
    "energy storage manufacturing", "gigafactory", "battery production",
    "lithium-ion", "cell manufacturing", "battery plant", "cell facility",
    "battery storage", "energy storage system", "gwh capacity", "battery pack",
    "advanced cell chemistry", "acc", "cathode production", "anode manufacturing",
    "battery materials", "cell assembly", "battery recycling"
]


def fetch_news_from_source(source_url):
    """Fetch news articles from a source website with enhanced search"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(source_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all links that might be news articles
        links = []
        category_links = []
        
        # Step 1: Process home page links
        for a in soup.find_all('a', href=True):
            link = a['href']
            
            # Fix relative URLs
            if not link.startswith('http'):
                if link.startswith('/'):
                    link = source_url.rstrip('/') + link
                else:
                    # Skip javascript and anchor links
                    if link.startswith('#') or link.startswith('javascript:'):
                        continue
                    link = source_url.rstrip('/') + '/' + link
            
            # Skip social media and utility links
            if any(domain in link.lower() for domain in [
                'facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com',
                'youtube.com', 'mailto:', 'whatsapp'
            ]):
                continue
            
            # Extract domain from source url
            source_domain = urlparse(source_url).netloc
            link_domain = urlparse(link).netloc
            
            # Only follow links from same domain or subdomains
            if source_domain not in link_domain:
                continue
            
            # Identify category pages for further exploration
            if any(term in link.lower() for term in [
                '/category/', '/section/', '/topics/', '/tag/', '/renewable-energy/',
                '/solar-energy/', '/energy-storage/', '/manufacturing/', '/india/'
            ]):
                category_links.append(link)
                
            # Check if it's likely a news article
            article_indicators = [
                'article', 'news', 'story', '/20', 'renewable', 'solar', 'battery', 
                'energy', 'manufacturing', 'gigafactory', 'production', 'capacity'
            ]
            
            # Enhanced article detection
            if any(term in link.lower() for term in article_indicators):
                # Avoid common non-article paths
                if not any(term in link.lower() for term in [
                    'about', 'contact', 'privacy', 'terms', 'login', 
                    'register', 'subscribe', 'newsletter'
                ]):
                    links.append(link)
        
        # Step 2: Follow category pages to find more articles (up to 5 category pages)
        category_links = list(set(category_links))[:5]  # Deduplicate and limit
        
        for category_url in category_links:
            try:
                cat_response = requests.get(category_url, headers=headers, timeout=10)
                cat_response.raise_for_status()
                cat_soup = BeautifulSoup(cat_response.text, 'html.parser')
                
                # Find articles on category page
                for a in cat_soup.find_all('a', href=True):
                    link = a['href']
                    
                    # Fix relative URLs
                    if not link.startswith('http'):
                        if link.startswith('/'):
                            link = source_url.rstrip('/') + link
                        else:
                            # Skip javascript and anchor links
                            if link.startswith('#') or link.startswith('javascript:'):
                                continue
                            link = source_url.rstrip('/') + '/' + link
                    
                    # Skip social media links
                    if any(domain in link.lower() for domain in [
                        'facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com',
                        'youtube.com', 'mailto:', 'whatsapp'
                    ]):
                        continue
                    
                    # Extract domain from source url
                    source_domain = urlparse(source_url).netloc
                    link_domain = urlparse(link).netloc
                    
                    # Only follow links from same domain or subdomains
                    if source_domain not in link_domain:
                        continue
                    
                    # Check if it's likely a news article (same criteria as above)
                    article_indicators = [
                        'article', 'news', 'story', '/20', 'renewable', 'solar', 'battery', 
                        'energy', 'manufacturing', 'gigafactory', 'production', 'capacity'
                    ]
                    
                    if any(term in link.lower() for term in article_indicators):
                        # Avoid common non-article paths
                        if not any(term in link.lower() for term in [
                            'about', 'contact', 'privacy', 'terms', 'login', 
                            'register', 'subscribe', 'newsletter'
                        ]):
                            links.append(link)
                            
            except Exception as e:
                logger.warning(f"Error fetching category page {category_url}: {str(e)}")
        
        # Deduplicate and return
        links = list(set(links))
        logger.info(f"Found {len(links)} potential article links at {source_url}")
        return links
    
    except Exception as e:
        logger.error(f"Error fetching from {source_url}: {str(e)}")
        return []


def extract_article_content(article_url):
    """Extract content from an article using the best available method"""
    if USE_NEWSPAPER:
        try:
            article = Article(article_url)
            article.download()
            article.parse()
            
            content = {
                'title': article.title,
                'text': article.text,
                'publish_date': article.publish_date
            }
            
            return content
        except Exception as e:
            logger.error(f"Error extracting with newspaper: {str(e)}")
            # Fall back to alternative method
            return extract_article_content_alternative(article_url)
    else:
        return extract_article_content_alternative(article_url)


def extract_article_content_alternative(article_url):
    """Alternative method to extract article content using trafilatura and BeautifulSoup"""
    try:
        # First try with trafilatura which often gives better results
        downloaded = trafilatura.fetch_url(article_url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            
            if text:
                # Try to extract title
                soup = BeautifulSoup(downloaded, 'html.parser')
                title_tag = soup.find('title')
                title = title_tag.text if title_tag else ""
                
                # Try to extract date
                publish_date = None
                meta_date = soup.find('meta', {'property': 'article:published_time'})
                if meta_date:
                    try:
                        publish_date = datetime.fromisoformat(meta_date['content'].replace('Z', '+00:00'))
                    except (ValueError, KeyError):
                        pass
                
                return {
                    'title': title,
                    'text': text,
                    'publish_date': publish_date
                }
                
        # Fallback to basic BeautifulSoup extraction
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(article_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try to find title
        title = ""
        title_tag = soup.find('h1') or soup.find('title')
        if title_tag:
            title = title_tag.text.strip()
        
        # Try to extract main content
        article_text = ""
        
        # Common article content containers
        content_elements = soup.select('article, .article-content, .entry-content, .post-content, .content, .story-content')
        
        if content_elements:
            for element in content_elements:
                paragraphs = element.find_all('p')
                if paragraphs:
                    article_text += ' '.join([p.text.strip() for p in paragraphs])
        else:
            # Try extracting all paragraphs
            paragraphs = soup.find_all('p')
            article_text = ' '.join([p.text.strip() for p in paragraphs])
        
        # Try to find date
        publish_date = None
        date_tags = soup.select('time, .date, .published, .post-date, [itemprop="datePublished"]')
        if date_tags:
            date_text = date_tags[0].text.strip()
            try:
                publish_date = datetime.strptime(date_text, "%Y-%m-%d")
            except ValueError:
                try:
                    publish_date = datetime.strptime(date_text, "%d-%m-%Y")
                except ValueError:
                    try:
                        publish_date = datetime.strptime(date_text, "%B %d, %Y")
                    except ValueError:
                        publish_date = None
        
        content = {
            'title': title,
            'text': article_text,
            'publish_date': publish_date
        }
        
        return content
    
    except Exception as e:
        logger.error(f"Error extracting with alternative method: {str(e)}")
        return {'title': '', 'text': '', 'publish_date': None}


# Initialize NLP resources
try:
    stop_words = set(stopwords.words('english'))
except:
    # Fallback if NLTK data is not available
    stop_words = set(['i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've", 
                      "you'll", "you'd", 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 
                      'himself', 'she', "she's", 'her', 'hers', 'herself', 'it', "it's", 'its', 'itself', 
                      'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 
                      'this', 'that', "that'll", 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 
                      'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 
                      'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 
                      'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through', 'during', 
                      'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 
                      'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 
                      'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 
                      'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 
                      's', 't', 'can', 'will', 'just', 'don', "don't", 'should', "should've", 'now', 'd', 'll', 
                      'm', 'o', 're', 've', 'y', 'ain', 'aren', "aren't", 'couldn', "couldn't", 'didn', "didn't", 
                      'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't", 'isn', "isn't", 
                      'ma', 'mightn', "mightn't", 'mustn', "mustn't", 'needn', "needn't", 'shan', "shan't", 
                      'shouldn', "shouldn't", 'wasn', "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn', "wouldn't"])

def preprocess_text(text):
    """Preprocess text for NLP analysis"""
    if not text:
        return []
        
    # Convert to lowercase and tokenize
    tokens = word_tokenize(text.lower())
    
    # Remove stopwords and non-alphabetic tokens
    filtered_tokens = [word for word in tokens if word.isalpha() and word not in stop_words]
    
    return filtered_tokens

def calculate_similarity(text1, text2):
    """Calculate semantic similarity between two texts using TF-IDF and cosine similarity"""
    if not text1 or not text2:
        return 0.0
        
    # Create TF-IDF vectorizer
    vectorizer = TfidfVectorizer()
    
    try:
        # Transform texts to TF-IDF vectors
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        
        # Calculate cosine similarity
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return similarity
    except Exception as e:
        logger.warning(f"Error calculating similarity: {str(e)}")
        return 0.0

def is_india_project(text):
    """Check if the article is about an Indian project using enhanced NLP techniques
    Returns a score between 0 and 1 indicating confidence"""
    if not text:
        return 0.0
        
    # Enhanced list of India-related terms with categorization
    primary_india_terms = [
        'india', 'indian', 'mnre', 'pli scheme', 'ministry of new and renewable energy',
        'made in india', 'make in india', 'pm-kusum', 'national solar mission',
        'atmanirbhar bharat', 'seci', 'solar energy corporation of india'
    ]
    
    secondary_india_terms = [
        'gujarat', 'maharashtra', 'tamil nadu', 'karnataka', 'telangana', 
        'rajasthan', 'uttar pradesh', 'madhya pradesh', 'andhra pradesh', 
        'delhi', 'mumbai', 'bengaluru', 'chennai', 'hyderabad', 'ahmedabad', 
        'pune', 'kolkata', 'jaipur', 'lucknow', 'nagpur', 'surat', 'indore',
        'odisha', 'bihar', 'jharkhand', 'chandigarh', 'haryana', 'uttarakhand',
        'inr', 'rupees', 'crore', 'lakh', 'bharat', 'niti aayog', 'nhai', 
        'ntpc', 'coal india', 'power grid'
    ]
    
    # Expanded list of Indian renewable energy companies
    indian_companies = [
        'tata', 'reliance', 'adani', 'birla', 'mahindra', 'bajaj', 
        'infosys', 'wipro', 'bhel', 'ntpc', 'ongc', 'iocl', 'gail', 
        'l&t', 'larsen', 'hindalco', 'jindal', 'suzlon', 'renew power', 
        'azure power', 'hero', 'waaree', 'vikram solar', 'premier energies',
        'goldi solar', 'websol', 'emmvee', 'reliance solar', 'adani solar',
        'tata power solar', 'luminous', 'panasonic india', 'havells',
        'avaada', 'acme solar', 'amp energy', 'amplus solar', 'greenко',
        'hfele india', 'first solar india', 'mundra solar', 'solex energy',
        'loom solar', 'insolation energy', 'alpex solar', 'ray power',
        'amara raja', 'exide', 'tata chemicals', 'isgec heavy engineering'
    ]
    
    text_lower = text.lower()
    score = 0.0
    
    # Method 1: Weighted keyword matching
    # Primary terms have higher weight (strong indicators of Indian projects)
    for term in primary_india_terms:
        if f" {term} " in f" {text_lower} ":  # Exact match
            score += 0.5
            break  # One strong match is sufficient
        elif term in text_lower:  # Partial match
            score += 0.3
            break
    
    # Secondary terms provide supporting evidence
    for term in secondary_india_terms:
        if f" {term} " in f" {text_lower} ":  # Exact match
            score += 0.3
            break
        elif term in text_lower:  # Partial match
            score += 0.2
            break
    
    # Company names provide additional supporting evidence
    for company in indian_companies:
        if f" {company} " in f" {text_lower} ":  # Exact match
            score += 0.2
            break
        elif company in text_lower:  # Partial match
            score += 0.1
            break
    
    # Method 2: NLP-based analysis for better accuracy
    try:
        # Create a reference text about Indian renewable energy
        india_reference = "India renewable energy solar manufacturing battery storage projects in states like Gujarat Maharashtra Tamil Nadu"
        
        # Calculate semantic similarity
        similarity_score = calculate_similarity(text_lower, india_reference)
        
        # Add scaled similarity score to total
        score += similarity_score * 0.3  # Weight the similarity score appropriately
    except Exception as e:
        logger.warning(f"NLP analysis failed: {str(e)}")
    
    # Cap the score at 1.0
    return min(score, 1.0)


def is_pipeline_project(text):
    """Check if the project is in pipeline (announced or under construction)"""
    pipeline_terms = [
        'announced', 'plan', 'to set up', 'will build', 'to construct',
        'to establish', 'under construction', 'building', 'developing',
        'in the works', 'upcoming', 'proposed', 'investment', 'breaking ground',
        'to invest', 'investing', 'capacity addition', 'new facility',
        'expansion', 'planned', 'to launch', 'to start', 'beginning', 
        'initiative', 'signing agreement', 'mou signed', 'partnership',
        'memorandum of understanding', 'joint venture', 'jv', 'pact',
        'tender', 'bid', 'awarded', 'contract', 'secured order'
    ]
    
    not_deployed_terms = [
        'operational', 'commissioned', 'completed', 'inaugurated',
        'opened', 'functioning', 'went online', 'now running',
        'already operating', 'fully functional', 'generating power',
        'producing', 'current output', 'in operation'
    ]
    
    # Capacity and investment terms indicate a project regardless of stage
    project_indicators = [
        'mw', 'gw', 'gwh', 'mwh', 'megawatt', 'gigawatt', 'million', 'billion',
        'capacity', 'crore', 'factory', 'manufacturing plant', 'production facility',
        'inr', 'usd', 'rupees', 'investment', 'funding'
    ]
    
    text_lower = text.lower()
    
    # Check standard pipeline terms
    is_pipeline = any(term in text_lower for term in pipeline_terms)
    is_not_deployed = not any(term in text_lower for term in not_deployed_terms)
    
    # Check for project indicators even if standard pipeline terms aren't found
    has_project_indicators = any(indicator in text_lower for indicator in project_indicators)
    
    # Return true if it's clearly in pipeline OR has project indicators but isn't deployed
    return (is_pipeline and is_not_deployed) or (has_project_indicators and is_not_deployed)


def determine_project_type(text):
    """Determine if the article is about a solar or battery project with enhanced detection"""
    text_lower = text.lower()
    
    # Additional solar keywords for more comprehensive detection
    expanded_solar_keywords = SOLAR_KEYWORDS + [
        "photovoltaic", "pv module", "solar power", "solar project", 
        "solar installation", "solar panel", "solar industry", "solar technology",
        "solar energy", "crystalline silicon", "mono perc", "polysilicon",
        "ingot", "wafer", "module assembly", "solar glass", "solar cells"
    ]
    
    # Additional battery keywords for more comprehensive detection
    expanded_battery_keywords = BATTERY_KEYWORDS + [
        "energy storage", "lithium ion", "li-ion", "battery cell", "battery tech",
        "battery storage", "energy storage system", "ess", "bess", "lto", "lfp",
        "lithium iron phosphate", "lithium titanate", "nmc", "cathode", "anode",
        "advanced chemistry cell", "acc", "electrolyte", "cell manufacturing"
    ]
    
    # Count keyword occurrences with weighted matching (whole words get more weight)
    solar_count = 0
    for keyword in expanded_solar_keywords:
        if f" {keyword} " in f" {text_lower} ":  # Exact/whole word match
            solar_count += 2
        elif keyword in text_lower:  # Partial match
            solar_count += 1
    
    battery_count = 0
    for keyword in expanded_battery_keywords:
        if f" {keyword} " in f" {text_lower} ":  # Exact/whole word match
            battery_count += 2
        elif keyword in text_lower:  # Partial match
            battery_count += 1
    
    # Determine project type based on keyword counts
    if solar_count > battery_count:
        return "Solar"  # Capitalize for consistency with database
    elif battery_count > solar_count:
        return "Battery"  # Capitalize for consistency with database
    elif solar_count > 0:  # If tied but solar terms exist
        return "Solar"
    elif battery_count > 0:  # If tied but battery terms exist
        return "Battery"
    else:
        return None  # Not a relevant project


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
            
        # Basic data
        data = {
            "Type": "Solar" if project_type == "solar" else "Battery",
            "Name": "",
            "Company": "",
            "Ownership": "Private",  # Default
            "PLI/Non-PLI": "Non PLI",  # Default
            "State": "NA",
            "Location": "NA",
            "Announcement Date": datetime.now().strftime("%d-%m-%Y"),
            "Category": "NA",
            "Input": "NA",
            "Output": "NA",
            "Cell Capacity": 0,
            "Module Capacity": 0,
            "Integration Capacity": 0,
            "Status": "Announced",  # Default
            "Land Acquisition": "NA",
            "Power Approval": "NA",
            "Environment Clearance": "NA",
            "ALMM Listing": "NA",
            "Investment USD": 0,
            "Investment INR": 0,
            "Expected Completion": "NA",
            "Last Updated": datetime.now().strftime("%d-%m-%Y"),
            "Source": article_url
        }
        
        title = content['title']
        text = content['text']
        
        # Extract project name from title
        if project_type == "solar" and "solar" in title.lower():
            data["Name"] = title.split(" - ")[0].strip()
        elif project_type == "battery" and "battery" in title.lower():
            data["Name"] = title.split(" - ")[0].strip()
        else:
            # Extract a sensible name from the title
            if " - " in title:
                data["Name"] = title.split(" - ")[0].strip()
            else:
                data["Name"] = title
                
            # Append project type if not in name
            if project_type not in data["Name"].lower():
                data["Name"] += f" {data['Type']} Project"
            
        # Extract company name
        potential_companies = []
        
        # Look for company patterns like "XYZ Ltd.", "XYZ Limited", "XYZ Corp"
        company_patterns = [
            r'([A-Z][a-zA-Z0-9]+ (?:[A-Z][a-zA-Z0-9]+ )*(?:Limited|Ltd\.?|Corp\.?|Corporation|Inc\.?|Private Limited|Pvt\.? Ltd\.?))',
            r'([A-Z][a-zA-Z0-9]+ (?:[A-Z][a-zA-Z0-9]+ )*(?:Energy|Solar|Power|Technologies|Renewables|Renewable))'
        ]
        
        for pattern in company_patterns:
            matches = re.findall(pattern, text)
            potential_companies.extend(matches)
            
        if potential_companies:
            # Sort by length to get the most complete company name
            potential_companies.sort(key=len, reverse=True)
            data["Company"] = potential_companies[0]
            
        # Extract capacity
        capacity_patterns = [
            r'(\d+(?:\.\d+)?)[ -](?:GW|gigawatt)',
            r'(\d+(?:\.\d+)?)[ -](?:MW|megawatt)',
            r'(\d+(?:\.\d+)?)[ -](?:GWh|gigawatt hour)',
            r'(\d+(?:\.\d+)?)[ -](?:MWh|megawatt hour)'
        ]
        
        for pattern in capacity_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                capacity = float(matches[0])
                
                # Convert MW to GW if needed
                if "MW" in pattern or "megawatt" in pattern:
                    capacity /= 1000
                    
                if project_type == "solar":
                    data["Module Capacity"] = capacity
                else:
                    data["Module Capacity"] = capacity
                break
                
        # Extract state
        indian_states = [
            "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
            "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
            "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
            "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
            "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal"
        ]
        
        for state in indian_states:
            if state.lower() in text.lower():
                data["State"] = state
                break
                
        # Extract location within state
        if data["State"] != "NA":
            # List of major cities in India
            major_cities = [
                "Mumbai", "Delhi", "Bangalore", "Bengaluru", "Hyderabad", "Chennai", 
                "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Surat", "Lucknow", 
                "Kanpur", "Nagpur", "Patna", "Indore", "Thane", "Bhopal", "Visakhapatnam",
                "Vadodara", "Coimbatore", "Ludhiana", "Kochi", "Agra", "Madurai", "Nashik",
                "Varanasi", "Dhanbad", "Amritsar", "Allahabad", "Ranchi", "Gwalior",
                "Jabalpur", "Vijayawada", "Jodhpur", "Raipur", "Kota", "Chandigarh"
            ]
            
            for city in major_cities:
                if city.lower() in text.lower():
                    data["Location"] = city
                    break
        
        # Extract investment
        investment_patterns = [
            r'(?:investment|invest|funding) of (?:Rs|INR)[.\s]*(\d+(?:\.\d+)?)\s*(?:crore|cr)',
            r'(?:investment|invest|funding) of (?:USD|US\$)[.\s]*(\d+(?:\.\d+)?)\s*(?:million|mn|m)',
            r'(?:investment|invest|funding) of (?:Rs|INR)[.\s]*(\d+(?:\.\d+)?)\s*(?:billion|bn)',
            r'(?:Rs|INR)[.\s]*(\d+(?:\.\d+)?)\s*(?:crore|cr) (?:investment|project)',
            r'(?:USD|US\$)[.\s]*(\d+(?:\.\d+)?)\s*(?:million|mn|m) (?:investment|project)'
        ]
        
        for pattern in investment_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                investment = float(matches[0])
                
                # Convert crore to billion for INR
                if "crore" in pattern or "cr" in pattern:
                    # 1 crore = 0.1 billion
                    data["Investment INR"] = investment * 0.1
                    # Approximate USD conversion (1 USD = 82.5 INR)
                    data["Investment USD"] = (investment * 0.1 * 1000) / 82.5
                elif "billion" in pattern or "bn" in pattern:
                    # It's already in billions
                    data["Investment INR"] = investment
                    # Convert to USD
                    data["Investment USD"] = (investment * 1000) / 82.5
                else:
                    # It's already in USD million
                    data["Investment USD"] = investment
                    # Convert to INR billion (1 USD = 82.5 INR)
                    data["Investment INR"] = (investment * 82.5) / 1000
                break
        
        # Extract expected completion year
        year_patterns = [
            r'(?:complete|finish|commission|operational)(?:d|ed)? by (?:the )?(?:year )?(\d{4})',
            r'(?:target|expected)(?:ed|ing)? (?:date|completion|to complete) (?:in|by) (?:the )?(?:year )?(\d{4})',
            r'(?:slated|scheduled) (?:for|to) (?:be )?(?:complete|finish|ready) (?:in|by) (\d{4})'
        ]
        
        for pattern in year_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                data["Expected Completion"] = matches[0]
                break
        
        # Check for PLI mentions
        if "pli" in text.lower() or "production linked incentive" in text.lower():
            data["PLI/Non-PLI"] = "PLI"
        
        # Extract status
        status_patterns = {
            "Planning": ["planning stage", "planned", "in planning"],
            "Announced": ["announced", "declaration", "declared"],
            "Land Acquisition": ["acquiring land", "land acquisition", "secured land"],
            "Under Construction": ["under construction", "being built", "construction underway", "building"],
            "Commissioning": ["commissioning", "trial", "testing phase"]
        }
        
        for status, keywords in status_patterns.items():
            if any(keyword in text.lower() for keyword in keywords):
                data["Status"] = status
                break
        
        # Set project-specific fields
        if project_type == "solar":
            data["Input"] = "Cells"
            data["Output"] = "Modules"
            
            # For cell-module integrated projects
            if "cell" in text.lower() and "module" in text.lower():
                data["Input"] = "Wafer"
                data["Output"] = "Cells, Modules"
                data["Cell Capacity"] = data["Module Capacity"]
                
            # For fully integrated projects
            if "ingot" in text.lower() and "wafer" in text.lower():
                data["Input"] = "Polysilicon"
                data["Output"] = "Ingots, Wafers, Cells, Modules"
        else:  # battery
            data["Input"] = "Battery Materials"
            data["Output"] = "Cells, Modules"
            data["Cell Capacity"] = data["Module Capacity"]
            
        return data
        
    except Exception as e:
        logger.error(f"Error extracting data from {article_url}: {str(e)}")
        return None
