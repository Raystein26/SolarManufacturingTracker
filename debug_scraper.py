"""
Debug script to test enhanced scraper functionality
"""

import logging
import sys
import enhanced_scraper
from nlp_processor import analyze_project_text
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_article(url=None, content=None):
    """Test article processing with verbose output"""
    if not url and not content:
        # Test article if none provided
        url = "https://mercomindia.com/premier-energies-partners-with-sino-american-for-solar-wafer-manufacturing/"
        content = """
        Premier Energies Partners with Sino-American Silicon for 5 GW Solar Wafer Manufacturing
        
        Premier Energies, an Indian solar cell and module manufacturer, has signed a memorandum of understanding (MoU) with Taiwan-based Sino-American Silicon Products to collaborate on setting up a 5 GW wafer manufacturing line in India.
        
        In this partnership, Sino-American Silicon Products will provide technological expertise and supply equipment to establish the project.
        
        Additionally, Surana Solar, a solar panel manufacturer, has also collaborated with the parties for the project.
        
        In September, Premier Energies announced its plans to establish a 4 GW monocrystalline ingot-to-wafer manufacturing line as part of its growth strategy and to complement its existing cell and module production lines.
        """
    
    logger.info(f"Testing article: {url}")
    
    # Check if it's about an Indian project
    india_score = enhanced_scraper.is_india_project(content)
    logger.info(f"India score: {india_score}")
    
    # Check if it's about a renewable energy project
    project_type_scores = enhanced_scraper.determine_project_type(content)
    logger.info(f"Project type scores: {json.dumps(project_type_scores, indent=2)}")
    
    # Find the most likely project type
    max_score = 0
    project_type = None
    
    for type_name, score in project_type_scores.items():
        if score > max_score:
            max_score = score
            project_type = type_name
    
    logger.info(f"Max project type: {project_type}, score: {max_score}")
    
    # Check if it's a pipeline project
    pipeline_score = enhanced_scraper.is_pipeline_project(content)
    logger.info(f"Pipeline score: {pipeline_score}")
    
    # Test NLP entity recognition
    nlp_results = analyze_project_text(content)
    logger.info(f"NLP results: {json.dumps(nlp_results, indent=2)}")
    
    # Now simulate the full extraction process
    project_data = enhanced_scraper.extract_project_data(url, content)
    
    if project_data:
        logger.info("===== Project detected successfully! =====")
        logger.info(f"Project data: {json.dumps(project_data, indent=2)}")
        return True
    else:
        logger.error("===== Project detection failed! =====")
        
        # Determine why detection failed
        min_threshold = 0.3 if project_type == 'solar' else 0.4
        min_pipeline_threshold = 0.3 if project_type == 'solar' else 0.4
        
        if max_score < min_threshold:
            logger.error(f"Failed because project type score too low: {max_score} < {min_threshold}")
        elif pipeline_score < min_pipeline_threshold:
            logger.error(f"Failed because pipeline score too low: {pipeline_score} < {min_pipeline_threshold}")
        else:
            logger.error("Failed for unknown reason")
            
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_article(url=sys.argv[1])
    else:
        test_article()