import re

def clean_project_name(name):
    """
    Clean up project names to extract just the core information
    for a cleaner Excel export
    """
    if not name:
        return "Unnamed Project"
        
    # If the name is very long, it's likely a news headline
    if len(name) > 80:
        # Try to extract key parts about the project
        extracted_name = ""
        
        # Look for manufacturing project mentions
        manufacturing_patterns = [
            r'([\w\s]+) (manufacturing|factory|plant|facility|gigafactory)',
            r'(manufacturing|factory|plant|facility|gigafactory) (of|for|by) ([\w\s]+)',
            r'([\w\s]+) to (set up|build|establish) ([\w\s]+) (manufacturing|factory|plant)',
            r'([\w\s]+) (cell|module|panel|battery) (manufacturing|factory|plant|production)'
        ]
        
        for pattern in manufacturing_patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                # Use the matched group that would contain the most relevant info
                for group in match.groups():
                    if group and len(group) > 10 and not group.lower() in ['manufacturing', 'factory', 'plant', 'facility', 'gigafactory']:
                        extracted_name = group.strip()
                        break
                
                if extracted_name:
                    break
        
        # If no match found with patterns, take first 50 chars and add ellipsis
        if not extracted_name:
            # Remove common headline prefixes
            cleaned = re.sub(r'^(breaking|news|update|exclusive):', '', name, flags=re.IGNORECASE).strip()
            extracted_name = cleaned[:50] + "..." if len(cleaned) > 50 else cleaned
            
        return extracted_name
    
    # Name is already concise
    return name