# Knowledge Transfer Document
## India Renewable Energy Infrastructure Intelligence Platform

### Project Handover and Critical Knowledge

---

## Table of Contents
1. [Project Context and History](#project-context-and-history)
2. [Critical System Dependencies](#critical-system-dependencies)
3. [Data Sources and Relationships](#data-sources-and-relationships)
4. [Business Logic and Rules](#business-logic-and-rules)
5. [Known Issues and Workarounds](#known-issues-and-workarounds)
6. [Vendor Relationships](#vendor-relationships)
7. [Performance Baselines](#performance-baselines)
8. [Emergency Contacts](#emergency-contacts)

---

## Project Context and History

### Project Genesis
- **Created**: November 2024
- **Original Purpose**: Track renewable energy manufacturing projects in India
- **Initial Scope**: Solar and battery manufacturing facilities
- **Evolution**: Expanded to 6 renewable energy categories with ML classification

### Key Milestones
1. **Phase 1**: Basic web scraping and manual data entry
2. **Phase 2**: Machine learning classification system
3. **Phase 3**: Advanced analytics and dashboard visualization
4. **Phase 4**: Training system and diagnostic capabilities
5. **Current State**: Production-ready with 80+ projects tracked

### Business Drivers
- India's 500 GW renewable energy target by 2030
- PLI (Production Linked Incentive) scheme tracking
- Investment flow monitoring for policy analysis
- Market intelligence for industry stakeholders

---

## Critical System Dependencies

### External Services

#### Database (PostgreSQL)
- **Critical Dependency**: All data storage
- **Connection**: DATABASE_URL environment variable
- **Backup Schedule**: Daily at 2 AM
- **Performance Impact**: System unusable without database
- **Recovery Time**: 4 hours maximum

#### OpenAI API (Optional)
- **Purpose**: Enhanced text analysis and summarization
- **API Key**: OPENAI_API_KEY environment variable
- **Fallback**: System operates without this service
- **Cost**: Pay-per-use (monitor usage)

### News Sources (Critical for Data Collection)
Primary sources monitored:
1. **Economic Times Energy** - Most reliable, structured content
2. **Mercom India** - High-quality renewable energy news
3. **PV Magazine India** - Solar industry focus
4. **Renewable Energy World** - Global perspective with India coverage
5. **Solar Power World** - Manufacturing and technology focus

**Source Reliability Ranking**:
- Tier 1 (95%+ reliability): Economic Times, Mercom India
- Tier 2 (80-95% reliability): PV Magazine, Renewable Energy World
- Tier 3 (60-80% reliability): General news sources

### Python Package Dependencies
**Critical packages that require careful version management**:
- `Flask 3.1.0` - Breaking changes in major versions
- `SQLAlchemy 2.0.40` - Migration required for 3.x
- `pandas 2.2.3` - Performance sensitive operations
- `scikit-learn 1.6.1` - Model compatibility issues

---

## Data Sources and Relationships

### Data Flow Architecture
```
News Sources → Web Scraper → Content Extractor → ML Classifier → Database
                     ↓              ↓              ↓            ↓
              Error Logging → Diagnostic → Training → Analytics Dashboard
```

### Critical Data Relationships

#### Project Classification Logic
```python
# Classification confidence thresholds (DO NOT MODIFY without testing)
CONFIDENCE_THRESHOLDS = {
    'india_project': 0.7,      # Must be India-related
    'pipeline_project': 0.6,   # Must be pipeline (not operational)
    'renewable_type': 0.8,     # Category classification
    'infrastructure': 0.75     # Must be infrastructure project
}
```

#### Capacity Data Standardization
- **Solar Manufacturing**: Cell, Module, Integration capacity in GW
- **Battery Manufacturing**: Cell, Module, Pack capacity in GWh
- **Wind**: Turbine manufacturing capacity in MW
- **Hydro**: Equipment manufacturing capacity in MW
- **Green Hydrogen**: Electrolyzer capacity in MW, production in tons/day
- **Biofuel**: Production capacity in million liters/year

#### Investment Data Handling
- **USD amounts**: Always in millions
- **INR amounts**: Always in billions (for consistency)
- **Conversion rate**: Not automated (requires manual validation)

---

## Business Logic and Rules

### Project Filtering Rules (Critical - DO NOT MODIFY)

#### Inclusion Criteria
1. **Geographic**: Must mention India, Indian states, or Indian cities
2. **Project Type**: Manufacturing, production facilities, or generation projects
3. **Status**: Announced, under construction, or recently commissioned
4. **Capacity**: Must have quantifiable capacity information
5. **Timeline**: Future projects or projects with recent announcements

#### Exclusion Rules (Implemented in cleanup_utility.py)
```python
EXCLUSION_KEYWORDS = [
    'conference', 'summit', 'discussion', 'interview',
    'policy announcement', 'general study', 'research paper',
    'maintenance', 'operational report', 'quarterly results'
]
```

### Data Quality Standards
- **Minimum Project Information**: Name, type, location, capacity OR investment
- **Source Validation**: Must have valid URL and publication date
- **Duplicate Prevention**: Company + location + capacity matching
- **Update Frequency**: Projects older than 3 years flagged for review

### Machine Learning Model Rules
- **Training Data Minimum**: 10 examples per category
- **Retraining Trigger**: Accuracy drops below 85%
- **Classification Confidence**: Require 80%+ confidence for auto-classification
- **Human Review**: Required for 70-80% confidence range

---

## Known Issues and Workarounds

### Current System Limitations

#### Issue 1: Website Structure Changes
**Symptom**: Scraping failures for specific sources
**Root Cause**: News websites modify HTML structure
**Workaround**: 
```python
# Multiple extraction methods implemented
try:
    content = newspaper_extraction(url)
except:
    try:
        content = trafilatura_extraction(url)
    except:
        content = beautifulsoup_extraction(url)
```
**Permanent Fix**: Implement headless browser scraping (Selenium/Playwright)

#### Issue 2: Classification Accuracy Drift
**Symptom**: New project types misclassified
**Root Cause**: Model trained on historical data patterns
**Workaround**: Regular model retraining with new examples
**Monitoring**: Weekly accuracy checks in diagnostic dashboard

#### Issue 3: Memory Usage Growth
**Symptom**: Application memory usage increases over time
**Root Cause**: Large dataset operations in pandas
**Workaround**: Process data in chunks, regular service restarts
**Monitoring**: Daily memory usage checks

#### Issue 4: Database Connection Pool Exhaustion
**Symptom**: "Too many connections" errors
**Root Cause**: Long-running queries and insufficient connection management
**Workaround**: Connection pool size increased to 20, query timeout set to 30s
**Fix**: Implement connection health checks and automatic recovery

### Data Quality Issues

#### Duplicate Project Detection
**Challenge**: Same project announced by multiple sources
**Solution**: Fuzzy matching on company + location + capacity
**Edge Cases**: Joint ventures, phased projects, capacity expansions

#### Incomplete Project Information
**Issue**: Projects missing key details (capacity, investment, timeline)
**Handling**: Store with available information, flag for manual review
**Priority**: Capacity information most critical for analysis

#### Currency and Unit Standardization
**Issue**: Mixed units (MW/GW, million/billion, USD/INR)
**Solution**: Standardization rules in data_processor.py
**Validation**: Automated checks for reasonable value ranges

---

## Vendor Relationships

### External Service Providers

#### News Source Relationships
- **Commercial Sources**: None (all public sources)
- **API Access**: None currently implemented
- **Rate Limiting**: Self-imposed 1 request per second per source
- **Terms of Service**: Regular compliance review required

#### Cloud Services
- **Database Hosting**: Self-managed PostgreSQL
- **Application Hosting**: Replit (development), self-hosted (production)
- **Backup Storage**: Local filesystem (upgrade to cloud recommended)

#### Optional Services
- **OpenAI**: Pay-per-use API access
- **Email Services**: SMTP configuration for notifications
- **SSL Certificates**: Let's Encrypt (free) or commercial provider

---

## Performance Baselines

### Expected System Performance

#### Response Times
- **Dashboard Load**: 2-3 seconds with 1000+ projects
- **Project List**: 1-2 seconds with filtering
- **Excel Export**: 30-60 seconds for full database
- **API Endpoints**: 200-500ms for single project queries

#### Data Processing
- **Daily Scraping**: 100-200 articles processed
- **Classification Speed**: 50 articles per minute
- **Database Writes**: 10-20 new projects per day
- **Training Process**: 5-10 minutes for model update

#### Resource Usage
- **Memory**: 500MB-2GB during normal operation
- **CPU**: 10-30% average, 80%+ during scraping
- **Database Size**: Growing 50-100MB per month
- **Network**: 10-50 Mbps during active scraping

### Performance Degradation Indicators
- **Response Time > 5 seconds**: Investigate database performance
- **Memory Usage > 4GB**: Restart application services
- **CPU Usage > 90% sustained**: Review scraping concurrency
- **Database Size > 10GB**: Implement data archival

---

## Emergency Contacts

### Technical Escalation

#### Database Issues
- **Primary**: Database administrator or hosting provider
- **Backup**: System administrator with PostgreSQL access
- **Emergency**: Use backup/recovery procedures in deployment guide

#### Application Issues
- **Primary**: Development team lead
- **Code Repository**: GitHub/GitLab access required
- **Deployment**: Server administrator with systemd access

#### Data Quality Issues
- **Primary**: Data analyst or domain expert
- **Secondary**: Business stakeholder familiar with renewable energy sector
- **Validation**: Cross-reference with industry reports

### Business Contacts

#### Stakeholder Communication
- **Primary Users**: Investment analysts, policy researchers
- **Feedback Channel**: User feedback form or direct communication
- **Feature Requests**: Product roadmap planning process

#### Compliance and Legal
- **Data Privacy**: Legal team for data protection compliance
- **Web Scraping**: Legal review of terms of service compliance
- **Industry Relations**: Renewable energy industry contacts

---

## Critical Operational Procedures

### Daily Operations Checklist
1. **Monitor scraping logs** for errors or failures
2. **Check database connectivity** and performance
3. **Review new projects** added in last 24 hours
4. **Verify system resource usage** (memory, CPU, disk)
5. **Confirm backup completion** and integrity

### Weekly Operations Checklist
1. **Analyze data quality metrics** and accuracy trends
2. **Review source reliability** and update configurations
3. **Check for system updates** and security patches
4. **Evaluate user feedback** and feature requests
5. **Update training data** if classification accuracy declines

### Monthly Operations Checklist
1. **Database maintenance** (VACUUM, ANALYZE, index optimization)
2. **Performance baseline review** and capacity planning
3. **Security assessment** and vulnerability scanning
4. **Backup and recovery testing** procedures
5. **Stakeholder communication** and usage reports

### Quarterly Operations Checklist
1. **Model retraining** and accuracy evaluation
2. **Technology stack review** and upgrade planning
3. **Source portfolio assessment** and expansion
4. **Business requirements review** and roadmap update
5. **Disaster recovery testing** and procedure validation

---

## Data Migration and Export Procedures

### Excel Export Formats
```python
# Standard export format (DO NOT MODIFY without stakeholder approval)
EXPORT_COLUMNS = [
    'Index', 'Type', 'Name', 'Company', 'Ownership', 'PLI/Non-PLI',
    'State', 'Location', 'Announcement Date', 'Category',
    'Cell Capacity (GW)', 'Module Capacity (GW)', 'Integration Capacity (GW)',
    'Investment (USD Million)', 'Investment (INR Billion)',
    'Status', 'Expected Completion', 'Source'
]
```

### Database Migration Scripts
```sql
-- Example migration for new fields
ALTER TABLE project ADD COLUMN new_field VARCHAR(100);
UPDATE project SET new_field = 'default_value' WHERE new_field IS NULL;

-- Index creation for performance
CREATE INDEX CONCURRENTLY idx_project_new_field ON project(new_field);
```

### API Data Formats
```json
{
  "project": {
    "id": 123,
    "type": "Solar",
    "name": "Project Name",
    "company": "Company Name",
    "capacities": {
      "cell": 5.0,
      "module": 3.0,
      "integration": 2.0
    },
    "investment": {
      "usd_million": 100.0,
      "inr_billion": 8.5
    },
    "metadata": {
      "created_at": "2024-01-01T00:00:00Z",
      "source": "https://example.com/article",
      "last_updated": "2024-01-01T00:00:00Z"
    }
  }
}
```

---

## Security and Compliance

### Data Protection
- **Personal Data**: No personal information collected or stored
- **Company Data**: Public information only from news sources
- **Access Controls**: Database-level permissions and application authentication
- **Audit Trail**: All data modifications logged with timestamps

### Web Scraping Compliance
- **robots.txt**: Respected for all sources
- **Rate Limiting**: Maximum 1 request per second per source
- **Fair Use**: Public information only, proper attribution
- **Terms of Service**: Regular review and compliance monitoring

### Security Measures
- **HTTPS**: All production traffic encrypted
- **Input Validation**: SQL injection and XSS protection
- **Database Security**: Encrypted connections and strong authentication
- **Server Security**: Regular security updates and firewall configuration

---

This knowledge transfer document contains the critical information needed for successful project handover. Regular updates ensure knowledge remains current and accurate for future team members.