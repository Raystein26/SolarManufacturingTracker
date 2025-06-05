# Technical Documentation
## India Renewable Energy Infrastructure Intelligence Platform

### Development Setup and Architecture Guide

---

## Table of Contents
1. [Development Environment Setup](#development-environment-setup)
2. [Architecture Overview](#architecture-overview)
3. [Database Schema](#database-schema)
4. [API Documentation](#api-documentation)
5. [Deployment Guide](#deployment-guide)
6. [Code Structure](#code-structure)
7. [Testing Strategy](#testing-strategy)
8. [Performance Monitoring](#performance-monitoring)

---

## Development Environment Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 13+
- Git
- Replit environment or equivalent hosting

### Environment Variables Required
```bash
DATABASE_URL=postgresql://user:password@host:port/database
SESSION_SECRET=your_session_secret_key
OPENAI_API_KEY=sk-your_openai_api_key (optional, for AI features)
```

### Installation Steps
```bash
# Clone repository
git clone <repository_url>
cd renewable-energy-tracker

# Install dependencies
pip install -r requirements.txt

# Database setup
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Initialize sample data (optional)
python add_sample_projects.py

# Start development server
python main.py
```

### Key Dependencies
- **Flask 3.1.0**: Web framework
- **SQLAlchemy 2.0.40**: Database ORM
- **pandas 2.2.3**: Data manipulation
- **scikit-learn 1.6.1**: Machine learning
- **BeautifulSoup4 4.13.4**: Web scraping
- **newspaper3k 0.2.8**: Article extraction

---

## Architecture Overview

### System Components
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Scraper   │───▶│  Data Processor │───▶│    Database     │
│                 │    │                 │    │                 │
│ - scraper.py    │    │ - models.py     │    │ - PostgreSQL    │
│ - enhanced_*    │    │ - data_mgr.py   │    │ - Projects      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Scheduler     │    │  ML Training    │    │  Web Interface  │
│                 │    │                 │    │                 │
│ - scheduler.py  │    │ - training_*    │    │ - routes.py     │
│ - progress_*    │    │ - diagnostic_*  │    │ - templates/    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Data Flow
1. **Scraping**: Automated collection from news sources
2. **Processing**: NLP classification and data extraction
3. **Storage**: Normalized database storage with validation
4. **Analysis**: ML-powered insights and categorization
5. **Presentation**: Web interface and API access

---

## Database Schema

### Core Tables

#### Projects Table
```sql
CREATE TABLE project (
    id SERIAL PRIMARY KEY,
    index INTEGER,
    type VARCHAR(50),              -- Solar, Battery, Wind, etc.
    name VARCHAR(200),
    company VARCHAR(200),
    ownership VARCHAR(50),
    pli_status VARCHAR(50),        -- PLI or Non-PLI
    state VARCHAR(100),
    location VARCHAR(100),
    announcement_date DATE,
    category VARCHAR(50),          -- Manufacturing, Generation, etc.
    
    -- Capacity fields (varies by type)
    generation_capacity FLOAT,     -- GW, MW
    storage_capacity FLOAT,        -- GWh, MWh
    cell_capacity FLOAT,           -- GW, GWh
    module_capacity FLOAT,         -- GW, GWh
    integration_capacity FLOAT,    -- GW, GWh
    electrolyzer_capacity FLOAT,   -- MW
    hydrogen_production FLOAT,     -- tons/day
    biofuel_capacity FLOAT,        -- million liters/year
    
    -- Investment
    investment_usd FLOAT,          -- USD Million
    investment_inr FLOAT,          -- INR Billion
    
    -- Status tracking
    status VARCHAR(50),
    expected_completion VARCHAR(50),
    last_updated DATE,
    source VARCHAR(500),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Sources Table
```sql
CREATE TABLE source (
    id SERIAL PRIMARY KEY,
    url VARCHAR(500) UNIQUE NOT NULL,
    name VARCHAR(200),
    description TEXT,
    last_checked TIMESTAMP,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Indexes for Performance
```sql
CREATE INDEX idx_project_type ON project(type);
CREATE INDEX idx_project_state ON project(state);
CREATE INDEX idx_project_status ON project(status);
CREATE INDEX idx_project_created ON project(created_at);
CREATE INDEX idx_source_url ON source(url);
```

---

## API Documentation

### REST Endpoints

#### Project Endpoints
```
GET /api/projects                 # List all projects
GET /api/projects?type=Solar      # Filter by type
GET /api/projects?state=Gujarat   # Filter by state
GET /api/project/{id}             # Get specific project
DELETE /api/project/{id}/delete   # Delete project
GET /api/project/{id}/export      # Export project to Excel
```

#### Source Management
```
GET /api/sources                  # List all sources
POST /api/sources                 # Add new source
PUT /api/sources/{id}             # Update source
DELETE /api/sources/{id}          # Remove source
```

#### Data Operations
```
POST /api/run-check               # Manual scraping trigger
GET /api/check-progress           # Scraping progress status
POST /api/export-excel            # Full database export
POST /api/import-excel            # Bulk data import
```

### Response Formats
```json
{
  "id": 123,
  "type": "Solar",
  "name": "Sample Solar Manufacturing Project",
  "company": "Example Corp",
  "state": "Gujarat",
  "cell_capacity": 5.0,
  "investment_usd": 100.0,
  "status": "Announced",
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

## Deployment Guide

### Production Deployment

#### Requirements
- **Server**: 2 CPU cores, 4GB RAM minimum
- **Database**: PostgreSQL with 10GB+ storage
- **Network**: HTTPS certificate required
- **Monitoring**: Application performance monitoring

#### Configuration
```python
# Production settings in app.py
app.config['DEBUG'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
    "pool_size": 10,
    "max_overflow": 20
}
```

#### Process Management
```bash
# Using Gunicorn for production
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 main:app

# Background scheduler
python scheduler.py &

# Process monitoring
ps aux | grep gunicorn
```

### Environment-Specific Configurations

#### Development
```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
python main.py
```

#### Staging
```bash
export FLASK_ENV=staging
gunicorn --bind 0.0.0.0:5000 --workers 2 main:app
```

#### Production
```bash
export FLASK_ENV=production
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 main:app
```

---

## Code Structure

### Module Organization
```
├── app.py                 # Flask application factory
├── main.py               # Application entry point
├── models.py             # Database models
├── routes.py             # Main web routes
├── routes_*.py           # Specialized route modules
├── scraper.py            # Web scraping engine
├── enhanced_scraper.py   # Advanced scraping features
├── project_tracker.py    # Orchestration logic
├── data_manager.py       # Import/export operations
├── training_module.py    # ML training system
├── diagnostic_tracker.py # System monitoring
├── scheduler.py          # Background tasks
├── cleanup_utility.py    # Data cleaning
├── progress_tracker.py   # Operation monitoring
├── data_processor.py     # Text processing utilities
└── templates/            # HTML templates
    ├── base.html
    ├── dashboard.html
    ├── projects.html
    └── ...
```

### Key Design Patterns

#### Module Initialization
```python
# Standard module pattern
import logging
from app import db
from models import Project

logger = logging.getLogger(__name__)

def main_function():
    """Module's primary functionality"""
    try:
        # Implementation
        logger.info("Operation completed")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise
```

#### Database Operations
```python
# Transaction safety pattern
try:
    project = Project(name="New Project", type="Solar")
    db.session.add(project)
    db.session.commit()
    logger.info(f"Project created: {project.id}")
except Exception as e:
    db.session.rollback()
    logger.error(f"Database error: {str(e)}")
    raise
```

#### Error Handling
```python
# Consistent error handling
def extract_data(url):
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return process_content(response.text)
    except requests.Timeout:
        logger.warning(f"Timeout accessing {url}")
        return None
    except requests.RequestException as e:
        logger.error(f"Request failed for {url}: {str(e)}")
        return None
```

---

## Testing Strategy

### Test Categories

#### Unit Tests
```python
# test_models.py
import unittest
from app import app, db
from models import Project

class TestProject(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        db.create_all()
    
    def test_project_creation(self):
        project = Project(name="Test", type="Solar")
        db.session.add(project)
        db.session.commit()
        self.assertIsNotNone(project.id)
```

#### Integration Tests
```python
# test_scraper.py
def test_article_extraction():
    url = "https://example.com/renewable-news"
    content = extract_article_content(url)
    self.assertIsNotNone(content)
    self.assertGreater(len(content), 100)
```

#### Performance Tests
```python
# test_performance.py
def test_database_query_performance():
    start_time = time.time()
    projects = Project.query.filter_by(type='Solar').all()
    end_time = time.time()
    self.assertLess(end_time - start_time, 1.0)  # Under 1 second
```

### Test Data Management
```python
# Create test fixtures
def create_test_project():
    return Project(
        name="Test Solar Project",
        type="Solar",
        company="Test Company",
        state="Test State",
        cell_capacity=1.0,
        status="Announced"
    )
```

---

## Performance Monitoring

### Key Metrics to Track

#### Application Performance
- Response time per endpoint
- Database query execution time
- Memory usage patterns
- CPU utilization during scraping

#### Data Quality Metrics
- Scraping success rate by source
- Classification accuracy over time
- Data completeness percentages
- Error rates and types

#### Business Metrics
- Number of projects tracked
- Daily/weekly growth rates
- User engagement patterns
- Export/API usage statistics

### Monitoring Implementation
```python
# Performance logging
import time
import functools

def monitor_performance(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"{func.__name__} completed in {execution_time:.2f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.2f}s: {str(e)}")
            raise
    return wrapper
```

### Database Performance Optimization
```sql
-- Query optimization examples
EXPLAIN ANALYZE SELECT * FROM project WHERE type = 'Solar' AND state = 'Gujarat';

-- Index usage monitoring
SELECT schemaname, tablename, attname, n_distinct, correlation 
FROM pg_stats WHERE tablename = 'project';

-- Connection monitoring
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';
```

---

## Critical Maintenance Tasks

### Daily Operations
- Monitor scraping job success rates
- Check database connection health
- Review error logs for new issues
- Verify backup completion

### Weekly Operations
- Analyze data quality metrics
- Review classification accuracy
- Update training data if needed
- Performance baseline comparison

### Monthly Operations
- Database maintenance (VACUUM, ANALYZE)
- Security update review
- Capacity planning assessment
- User feedback analysis

### Quarterly Operations
- Model retraining evaluation
- Source reliability assessment
- Technology stack updates
- Performance optimization review

---

## Troubleshooting Common Issues

### Database Connection Issues
```python
# Connection test
try:
    db.session.execute('SELECT 1')
    print("Database connection OK")
except Exception as e:
    print(f"Database connection failed: {e}")
```

### Scraping Failures
```python
# Debug scraping issues
def debug_scraper(url):
    try:
        response = requests.get(url, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Content length: {len(response.text)}")
        return response.text[:500]  # First 500 chars
    except Exception as e:
        print(f"Scraping failed: {e}")
```

### Performance Issues
```python
# Database query optimization
from sqlalchemy import text

# Slow query analysis
slow_queries = db.session.execute(text("""
    SELECT query, mean_time, calls 
    FROM pg_stat_statements 
    WHERE mean_time > 1000 
    ORDER BY mean_time DESC
"""))
```

---

## Security Considerations

### Input Validation
```python
# URL validation example
import validators

def validate_source_url(url):
    if not validators.url(url):
        raise ValueError("Invalid URL format")
    if not url.startswith(('http://', 'https://')):
        raise ValueError("URL must use HTTP or HTTPS")
    return url
```

### Data Sanitization
```python
# HTML content cleaning
from bs4 import BeautifulSoup

def clean_html_content(html):
    soup = BeautifulSoup(html, 'html.parser')
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    return soup.get_text()
```

### Access Control
```python
# Role-based access example
from functools import wraps

def requires_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
```

---

This technical documentation provides the foundation for developers to understand, maintain, and extend the renewable energy tracking platform. Regular updates to this documentation ensure knowledge continuity and system reliability.