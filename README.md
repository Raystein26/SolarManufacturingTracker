# India Renewable Energy Infrastructure Intelligence Platform

An advanced data science platform for tracking and analyzing renewable energy manufacturing projects across India, utilizing sophisticated web scraping, machine learning classification, and real-time analytics.

## 🎯 Project Overview

This platform serves as a comprehensive intelligence system for India's renewable energy infrastructure sector, automatically collecting and analyzing project announcements across six major categories: Solar, Battery Storage, Wind, Hydro, Green Hydrogen, and Biofuel manufacturing.

### Key Features
- **Automated Data Collection**: Continuous monitoring of 20+ renewable energy news sources
- **AI-Powered Classification**: Machine learning models for project categorization and relevance scoring
- **Real-Time Analytics**: Interactive dashboards with capacity tracking and investment analysis
- **Export Capabilities**: Excel-based reporting with customizable formats
- **Training System**: Supervised learning for continuous model improvement

## 📊 Current Status

- **Projects Tracked**: 80+ verified renewable energy infrastructure projects
- **Data Sources**: 15+ active news sources with 95% uptime
- **Classification Accuracy**: 90%+ for project type identification
- **Update Frequency**: Daily automated collection with 24-48 hour announcement capture

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 13+
- 4GB RAM minimum (8GB recommended)

### Installation
```bash
# Clone and setup
git clone <repository-url>
cd renewable-energy-tracker

# Install dependencies
pip install -r requirements.txt

# Configure environment
export DATABASE_URL=postgresql://user:password@host:port/database
export SESSION_SECRET=your-session-secret

# Initialize database
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Start application
python main.py
```

### Access Points
- **Web Interface**: http://localhost:5000
- **Dashboard**: http://localhost:5000/dashboard
- **API**: http://localhost:5000/api/projects

## 📚 Documentation

### For Users
- **[User Manual](USER_MANUAL.md)**: Complete feature guide and usage instructions
- **[Product Requirements](PRD.md)**: Business requirements and success metrics

### For Developers
- **[Technical Documentation](TECHNICAL_DOCUMENTATION.md)**: Architecture and development guide
- **[Deployment Guide](DEPLOYMENT_GUIDE.md)**: Production setup and operations
- **[Knowledge Transfer](KNOWLEDGE_TRANSFER.md)**: Critical system knowledge and procedures

## 🏗️ Architecture

### Technology Stack
- **Backend**: Python 3.11, Flask 3.1.0, SQLAlchemy 2.0.40
- **Database**: PostgreSQL with optimized indexing
- **ML/NLP**: scikit-learn, NLTK, spaCy for classification
- **Web Scraping**: BeautifulSoup4, newspaper3k, trafilatura
- **Frontend**: Bootstrap 5.3, Chart.js, responsive design
- **Deployment**: Gunicorn, Nginx, systemd services

### Core Components
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Scraper   │───▶│ ML Classifier   │───▶│    Database     │
│                 │    │                 │    │                 │
│ • Multi-source  │    │ • 6 categories  │    │ • PostgreSQL    │
│ • Rate limited  │    │ • Confidence    │    │ • 50+ fields    │
│ • Error recovery│    │ • Training      │    │ • Performance   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Scheduler     │    │   Analytics     │    │ Web Interface   │
│                 │    │                 │    │                 │
│ • Daily runs    │    │ • Dashboards    │    │ • CRUD ops      │
│ • Monitoring    │    │ • Exports       │    │ • Visualizations│
│ • Diagnostics   │    │ • APIs          │    │ • Mobile ready  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📈 Data Categories

### Renewable Energy Types
1. **Solar Manufacturing**: Cell, module, and integration capacity (GW)
2. **Battery Storage**: Manufacturing capacity for energy storage systems (GWh)
3. **Wind Energy**: Turbine and component manufacturing (MW)
4. **Hydro Power**: Equipment manufacturing and project development (MW)
5. **Green Hydrogen**: Electrolyzer capacity and production facilities (MW, tons/day)
6. **Biofuel**: Production capacity for renewable fuels (million liters/year)

### Data Fields
- **Project Information**: Name, company, location, status, timeline
- **Capacity Data**: Type-specific capacity in standardized units
- **Investment**: USD millions and INR billions with validation
- **Policy Context**: PLI scheme participation and government support
- **Source Attribution**: Full traceability to original announcements

## 🔧 Configuration

### Environment Variables
```bash
# Required
DATABASE_URL=postgresql://user:password@host:port/database
SESSION_SECRET=secure-random-string

# Optional
OPENAI_API_KEY=sk-your-openai-key  # For enhanced AI features
```

### Performance Tuning
```python
# Database optimization
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_size": 10,
    "max_overflow": 20,
    "pool_recycle": 300,
    "pool_pre_ping": True
}

# Scraping configuration
SCRAPING_DELAY = 1.0  # Seconds between requests
TIMEOUT_SECONDS = 30  # Request timeout
MAX_CONCURRENT = 5    # Parallel source processing
```

## 📊 API Reference

### Project Endpoints
```bash
# List projects with filtering
GET /api/projects?type=Solar&state=Gujarat

# Get specific project
GET /api/project/{id}

# Export to Excel
GET /api/project/{id}/export

# Delete project
DELETE /api/project/{id}/delete
```

### Data Operations
```bash
# Trigger manual scraping
POST /api/run-check

# Check scraping progress
GET /api/check-progress

# Export full database
POST /api/export-excel

# Import training data
POST /api/import-excel
```

## 🎯 Use Cases

### Investment Analysis
- Track project pipelines by capacity and investment
- Monitor competitor announcements and market share
- Analyze geographic distribution and state-wise development
- Export data for financial modeling and forecasting

### Policy Research
- Assess PLI scheme effectiveness and adoption rates
- Monitor manufacturing capacity versus national targets
- Analyze regional development patterns and policy impact
- Generate reports for government and academic research

### Market Intelligence
- Daily monitoring of industry announcements
- Technology trend analysis and adoption patterns
- Supply chain mapping and vendor relationships
- Competitive landscape assessment

## 🔍 Quality Assurance

### Data Validation
- **Source Verification**: URLs validated and content authenticated
- **Duplicate Detection**: Fuzzy matching on company, location, and capacity
- **Range Validation**: Capacity and investment amounts within reasonable bounds
- **India Focus**: Geographic filtering with 95% accuracy

### Classification Standards
- **Confidence Thresholds**: 80%+ required for automated classification
- **Human Review**: Required for 70-80% confidence range
- **Training Data**: Minimum 10 examples per renewable energy category
- **Model Performance**: Quarterly accuracy assessment and retraining

## 🚨 Monitoring and Alerts

### System Health
- **Database Connectivity**: Real-time connection monitoring
- **Scraping Performance**: Success rates and error tracking
- **Resource Usage**: Memory, CPU, and disk utilization
- **Response Times**: API and web interface performance

### Data Quality Metrics
- **Daily Project Additions**: New project capture rate
- **Source Reliability**: Success rate per news source
- **Classification Accuracy**: Model performance tracking
- **Data Completeness**: Required field population rates

## 🛡️ Security and Compliance

### Data Protection
- **Public Information Only**: No personal data collection
- **Source Attribution**: Proper credit to original publishers
- **Access Controls**: Role-based permissions and audit logging
- **Encryption**: HTTPS for all data transmission

### Web Scraping Ethics
- **Rate Limiting**: Maximum 1 request per second per source
- **robots.txt Compliance**: Automatic respect for crawling directives
- **Fair Use**: Educational and research purpose usage
- **Terms of Service**: Regular compliance review and monitoring

## 📞 Support and Contact

### Technical Issues
- Review logs in `/var/log/` directory for error details
- Check database connectivity and resource utilization
- Consult troubleshooting guide in technical documentation
- Monitor diagnostic dashboard for system health metrics

### Business Questions
- Refer to user manual for feature explanations
- Check data quality metrics in diagnostic interface
- Review export formats and API documentation
- Contact domain experts for renewable energy sector questions

## 🗺️ Roadmap

### Near-term Enhancements
- **Geographic Visualization**: Interactive maps with project locations
- **Advanced Analytics**: Predictive modeling for capacity forecasting
- **API Expansion**: GraphQL interface for complex queries
- **Mobile App**: Native mobile application for field access

### Long-term Vision
- **Multi-country Support**: Expansion beyond India to regional coverage
- **AI Integration**: Enhanced GPT-powered analysis and insights
- **Real-time Alerts**: Notification system for critical project updates
- **Enterprise Features**: Advanced user management and customization

## 📝 License and Attribution

This project tracks publicly available information about renewable energy infrastructure development in India. All data sources are properly attributed, and the platform respects fair use principles for educational and research purposes.

**Created by**: Sahaya Ray  
**Purpose**: Academic and policy research  
**Data Sources**: Public news and government announcements  
**Updates**: Continuous development with regular feature additions

---

For detailed technical information, deployment procedures, or business requirements, please refer to the comprehensive documentation files included in this repository.

**Documentation Index**:
- [USER_MANUAL.md](USER_MANUAL.md) - Complete user guide
- [PRD.md](PRD.md) - Product requirements document
- [TECHNICAL_DOCUMENTATION.md](TECHNICAL_DOCUMENTATION.md) - Developer guide
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Production setup
- [KNOWLEDGE_TRANSFER.md](KNOWLEDGE_TRANSFER.md) - Critical system knowledge

---
*India Renewable Energy Infrastructure Intelligence Platform - Empowering informed decision-making in sustainable energy development*