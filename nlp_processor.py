"""
NLP Processor for enhanced entity recognition in renewable energy projects

This module uses spaCy and custom patterns to extract key information from
news articles, including company names, locations, capacities, and dates.
"""

import re
import logging
import spacy
from datetime import datetime
from typing import Dict, List, Tuple, Union, Optional

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
    logger.info("Loaded spaCy model successfully")
except Exception as e:
    logger.error(f"Error loading spaCy model: {e}")
    nlp = None

# Define custom patterns for renewable energy entities
CAPACITY_PATTERNS = [
    r'(\d+(?:\.\d+)?)\s*(?:GW|MW|kW)(?:h)?',  # For power capacity
    r'(\d+(?:\.\d+)?)\s*(?:MWh|GWh|kWh)',     # For energy storage
    r'(\d+(?:\.\d+)?)\s*(?:tons?|tonnes?)',   # For hydrogen production
    r'(\d+(?:\.\d+)?)\s*(?:KTPA|mtpa)',       # For annual production
    r'(\d+(?:\.\d+)?)\s*(?:million\s*liters?|ML)', # For biofuel
]

INVESTMENT_PATTERNS = [
    r'(?:investment|invest|funding|fund)\s*(?:of|worth|amounting to)?\s*(?:Rs\.?|INR|₹)?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:crore|cr|billion|bn|million|mn|lakh)',
    r'(?:investment|invest|funding|fund)\s*(?:of|worth|amounting to)?\s*\$?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:billion|bn|million|mn|USD)'
]

COMPLETION_PATTERNS = [
    r'(?:expected|scheduled|planned|target(?:ed)?)\s*(?:to|for)?\s*(?:complete|finish|commission|be\s*operational|be\s*completed)\s*(?:by|in|on)?\s*([A-Z][a-z]+\s+\d{4}|\d{4}(?:-\d{2})?(?:-\d{2})?|Q[1-4]\s+\d{4}|[A-Z][a-z]+\s+\d{1,2}(?:st|nd|rd|th)?\s*,?\s*\d{4})',
    r'(?:completion|commissioning)\s*(?:date|scheduled|expected|planned|target(?:ed)?)\s*(?:for|in|by|on)?\s*([A-Z][a-z]+\s+\d{4}|\d{4}(?:-\d{2})?(?:-\d{2})?|Q[1-4]\s+\d{4}|[A-Z][a-z]+\s+\d{1,2}(?:st|nd|rd|th)?\s*,?\s*\d{4})'
]

INDIAN_STATES = [
    'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
    'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
    'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
    'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu', 'Telangana',
    'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
    'Andaman and Nicobar Islands', 'Chandigarh', 'Dadra and Nagar Haveli and Daman and Diu',
    'Delhi', 'Jammu and Kashmir', 'Ladakh', 'Lakshadweep', 'Puducherry'
]

def extract_entities(text: str) -> Dict[str, Union[str, float, List[dict]]]:
    """
    Extract named entities and other relevant information from text
    
    Args:
        text: Article text content
        
    Returns:
        Dictionary with extracted entities categorized
    """
    if not text or not nlp:
        return {}
    
    # Process text with spaCy
    doc = nlp(text)
    
    # Initialize results dictionary
    results = {
        'companies': extract_companies(doc, text),
        'locations': extract_locations(doc, text),
        'dates': extract_dates(doc, text),
        'capacities': extract_capacities(text),
        'investment': extract_investment(text),
        'completion_date': extract_completion_date(text),
        'state': extract_indian_state(text)
    }
    
    return results

def extract_companies(doc, text: str) -> List[dict]:
    """Extract company names with confidence scores"""
    companies = []
    
    # Get companies from spaCy's named entity recognition
    for ent in doc.ents:
        if ent.label_ == "ORG":
            companies.append({
                'name': ent.text,
                'confidence': 0.7,
                'method': 'spacy_ner'
            })
    
    # Look for companies followed by Ltd/Limited/Corp/Inc patterns
    company_patterns = [
        r'([A-Z][A-Za-z\s]+)(?:\s+(?:Limited|Ltd\.?|Corporation|Corp\.?|Inc\.?|Private|Pvt\.?|L\.?L\.?C\.?))',
        r'([A-Z][A-Za-z\s]+)\s+(?:has|announced|plans|will|to)\s+(?:develop|build|construct|install|commission)'
    ]
    
    for pattern in company_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            company_name = match.group(1).strip()
            if len(company_name) > 3 and company_name not in [c['name'] for c in companies]:
                companies.append({
                    'name': company_name,
                    'confidence': 0.8,
                    'method': 'pattern_match'
                })
    
    # Remove duplicates and sort by confidence
    unique_companies = []
    seen_names = set()
    
    for company in sorted(companies, key=lambda x: x['confidence'], reverse=True):
        normalized_name = company['name'].lower()
        if normalized_name not in seen_names and len(company['name']) > 3:
            unique_companies.append(company)
            seen_names.add(normalized_name)
    
    return unique_companies[:3]  # Return top 3 most confident matches

def extract_locations(doc, text: str) -> List[dict]:
    """Extract location information with confidence scores"""
    locations = []
    
    # Get locations from spaCy's named entity recognition
    for ent in doc.ents:
        if ent.label_ == "GPE" or ent.label_ == "LOC":
            if len(ent.text) > 2:  # Filter out very short names
                locations.append({
                    'name': ent.text,
                    'confidence': 0.7,
                    'method': 'spacy_ner'
                })
    
    # Pattern for locations mentioned with prepositions
    location_patterns = [
        r'(?:in|at|near|around)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        r'project\s+(?:in|at|near)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
    ]
    
    for pattern in location_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            location_name = match.group(1).strip()
            if len(location_name) > 2 and location_name not in [loc['name'] for loc in locations]:
                locations.append({
                    'name': location_name,
                    'confidence': 0.6,
                    'method': 'pattern_match'
                })
    
    # Remove duplicates and sort by confidence
    unique_locations = []
    seen_names = set()
    
    for location in sorted(locations, key=lambda x: x['confidence'], reverse=True):
        normalized_name = location['name'].lower()
        if normalized_name not in seen_names:
            unique_locations.append(location)
            seen_names.add(normalized_name)
    
    return unique_locations[:3]  # Return top 3 most confident matches

def extract_dates(doc, text: str) -> List[dict]:
    """Extract date information with confidence scores"""
    dates = []
    
    # Get dates from spaCy's named entity recognition
    for ent in doc.ents:
        if ent.label_ == "DATE":
            dates.append({
                'text': ent.text,
                'confidence': 0.7,
                'method': 'spacy_ner'
            })
    
    # Pattern for date formats
    date_patterns = [
        r'([A-Z][a-z]+\s+\d{1,2}(?:st|nd|rd|th)?,\s*\d{4})',  # May 15th, 2025
        r'(\d{1,2}(?:st|nd|rd|th)?\s+[A-Z][a-z]+,?\s*\d{4})',  # 15th May 2025
        r'(\d{4}-\d{2}-\d{2})'  # 2025-05-15
    ]
    
    for pattern in date_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            date_text = match.group(1).strip()
            dates.append({
                'text': date_text,
                'confidence': 0.8,
                'method': 'pattern_match'
            })
    
    # Remove duplicates and sort by confidence
    unique_dates = []
    seen_texts = set()
    
    for date in sorted(dates, key=lambda x: x['confidence'], reverse=True):
        if date['text'] not in seen_texts:
            unique_dates.append(date)
            seen_texts.add(date['text'])
    
    return unique_dates[:3]  # Return top 3 most confident matches

def extract_capacities(text: str) -> List[dict]:
    """Extract capacity information with value, unit and confidence scores"""
    capacities = []
    
    for pattern in CAPACITY_PATTERNS:
        matches = re.finditer(pattern, text)
        for match in matches:
            full_match = match.group(0)
            value = float(match.group(1))
            
            # Extract unit
            unit_match = re.search(r'[A-Za-z]+', full_match[match.group(1).__len__():])
            unit = unit_match.group(0) if unit_match else ""
            
            capacities.append({
                'value': value,
                'unit': unit,
                'text': full_match,
                'confidence': 0.85,
                'method': 'regex'
            })
    
    # Remove duplicates and sort by confidence
    unique_capacities = []
    seen_texts = set()
    
    for capacity in sorted(capacities, key=lambda x: x['confidence'], reverse=True):
        if capacity['text'] not in seen_texts:
            unique_capacities.append(capacity)
            seen_texts.add(capacity['text'])
    
    return unique_capacities

def extract_investment(text: str) -> Optional[Dict[str, Union[float, str, float]]]:
    """Extract investment information with value, currency and confidence scores"""
    for pattern in INVESTMENT_PATTERNS:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            full_text = match.group(0)
            value_str = match.group(1).replace(',', '')
            
            try:
                value = float(value_str)
                
                # Determine currency and scale
                currency = "INR" if re.search(r'Rs\.?|INR|₹', full_text) else "USD"
                scale = None
                scale_name = ""
                
                if re.search(r'billion|bn', full_text, re.IGNORECASE):
                    scale = 1e9
                    scale_name = "billion"
                elif re.search(r'million|mn', full_text, re.IGNORECASE):
                    scale = 1e6
                    scale_name = "million"
                elif re.search(r'crore|cr', full_text, re.IGNORECASE):
                    scale = 1e7  # 1 crore = 10 million
                    scale_name = "crore"
                elif re.search(r'lakh', full_text, re.IGNORECASE):
                    scale = 1e5  # 1 lakh = 100,000
                    scale_name = "lakh"
                
                if scale:
                    return {
                        'value': value,
                        'currency': currency,
                        'scale': scale_name,
                        'normalized_value': value * scale,
                        'text': full_text,
                        'confidence': 0.8
                    }
            except ValueError:
                continue
    
    return None

def extract_completion_date(text: str) -> Optional[Dict[str, Union[str, float]]]:
    """Extract project completion date information"""
    for pattern in COMPLETION_PATTERNS:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            date_text = match.group(1)
            full_text = match.group(0)
            
            return {
                'date_text': date_text,
                'full_text': full_text,
                'confidence': 0.75
            }
    
    return None

def extract_indian_state(text: str) -> Optional[Dict[str, Union[str, float]]]:
    """Extract Indian state name from text"""
    for state in INDIAN_STATES:
        # Look for exact matches
        if state in text:
            return {
                'name': state,
                'confidence': 0.9
            }
        
        # Also look for patterns like "in Karnataka" or "project in Karnataka"
        pattern = rf'\b(?:in|at|near|around|located\s+in)\s+{state}\b'
        if re.search(pattern, text):
            return {
                'name': state,
                'confidence': 0.95
            }
    
    return None

def analyze_project_text(text: str, title: str = "") -> Dict:
    """
    Analyze project text to extract all relevant entities
    
    Args:
        text: Main article content
        title: Article title (optional)
        
    Returns:
        Dictionary with all extracted information
    """
    full_text = f"{title}\n\n{text}" if title else text
    
    try:
        entities = extract_entities(full_text)
        
        # Format the results for easier consumption by the main application
        results = {
            "project_name": extract_project_name(full_text, entities),
            "companies": [c['name'] for c in entities.get('companies', [])[:1]] if entities.get('companies') else [],
            "location": [l['name'] for l in entities.get('locations', [])[:1]] if entities.get('locations') else [],
            "state": entities.get('state', {}).get('name') if entities.get('state') else None,
            "announcement_date": format_date(entities.get('dates', [])[:1]),
            "capacities": entities.get('capacities', []),
            "investment": entities.get('investment'),
            "completion_date": entities.get('completion_date', {}).get('date_text') if entities.get('completion_date') else None,
            "raw_entities": entities  # Include all raw entity data for debugging
        }
        
        return results
    except Exception as e:
        logger.error(f"Error analyzing project text: {e}")
        return {"error": str(e)}

def extract_project_name(text: str, entities: Dict) -> Optional[str]:
    """Extract the most likely project name from text and entities"""
    # Try to find project name patterns
    project_patterns = [
        r'([A-Z][A-Za-z0-9\s\-]+(?:Project|project|Plant|plant|Park|park|Facility|facility))',
        r'(?:announced|unveiled|launched)\s+(?:a|its|their)\s+([A-Z][A-Za-z0-9\s\-]+(?:Project|project|Plant|plant|Park|park|Facility|facility))',
        r'(?:new|planned)\s+([A-Z][A-Za-z0-9\s\-]+(?:Project|project|Plant|plant|Park|park|Facility|facility))'
    ]
    
    for pattern in project_patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            project_name = match.group(1).strip()
            if len(project_name) > 5 and len(project_name) < 100:
                return project_name
    
    # If no clear project name, try to construct one from entities
    if entities.get('companies') and (
        entities.get('capacities') or 
        entities.get('locations') or 
        ('Battery' in text or 'Solar' in text or 'Wind' in text)
    ):
        company = entities['companies'][0]['name']
        
        # Determine project type
        project_type = ""
        if 'Solar' in text or 'solar' in text:
            project_type = "Solar"
        elif 'Battery' in text or 'battery' in text:
            project_type = "Battery"
        elif 'Wind' in text or 'wind' in text:
            project_type = "Wind"
        elif 'Hydro' in text or 'hydro' in text:
            project_type = "Hydro"
        elif 'Hydrogen' in text or 'hydrogen' in text:
            project_type = "Hydrogen"
        
        # Get capacity if available
        capacity_str = ""
        if entities.get('capacities'):
            cap = entities['capacities'][0]
            capacity_str = f"{cap['value']} {cap['unit']} "
        
        # Get location if available
        location_str = ""
        if entities.get('locations'):
            location_str = f" in {entities['locations'][0]['name']}"
        elif entities.get('state'):
            location_str = f" in {entities['state']['name']}"
        
        return f"{company} {capacity_str}{project_type} Project{location_str}".strip()
    
    return None

def format_date(dates: List[Dict]) -> Optional[str]:
    """Format extracted date into a standard format"""
    if not dates:
        return None
    
    date_text = dates[0]['text']
    
    # Try different parsing strategies
    try:
        # If it's already in ISO format
        if re.match(r'\d{4}-\d{2}-\d{2}', date_text):
            return date_text
        
        # Try common formats
        for fmt in [
            '%B %d, %Y',  # May 15, 2025
            '%B %dst, %Y', '%B %dnd, %Y', '%B %drd, %Y', '%B %dth, %Y',  # May 1st, 2025
            '%d %B %Y',  # 15 May 2025
            '%d-%b-%Y',  # 15-May-2025
        ]:
            try:
                dt = datetime.strptime(date_text.replace(',', ''), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
    except Exception:
        pass
    
    return date_text  # Return original if parsing fails

def normalize_capacity(capacity: Dict) -> Optional[Tuple[float, str]]:
    """
    Normalize capacity to standard units (GW, MWh, etc.)
    
    Returns:
        Tuple of (value, unit) or None if can't normalize
    """
    if not capacity:
        return None
    
    value = capacity['value']
    unit = capacity['unit'].upper()
    
    # Handle power capacity
    if unit in ['MW', 'MEGAWATT', 'MEGAWATTS']:
        return (value / 1000, 'GW')
    elif unit in ['KW', 'KILOWATT', 'KILOWATTS']:
        return (value / 1000000, 'GW')
    elif unit in ['GW', 'GIGAWATT', 'GIGAWATTS']:
        return (value, 'GW')
    
    # Handle energy storage
    if unit in ['MWH', 'MEGAWATTHOUR', 'MEGAWATTHOURS']:
        return (value / 1000, 'GWh')
    elif unit in ['KWH', 'KILOWATTHOUR', 'KILOWATTHOURS']:
        return (value / 1000000, 'GWh')
    elif unit in ['GWH', 'GIGAWATTHOUR', 'GIGAWATTHOURS']:
        return (value, 'GWh')
    
    # Other capacity types
    return (value, unit)