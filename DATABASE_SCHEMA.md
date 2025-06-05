# Database Schema Documentation
## India Renewable Energy Infrastructure Intelligence Platform

### Comprehensive Database Design and Structure

---

## Table of Contents
1. [Schema Overview](#schema-overview)
2. [Core Tables](#core-tables)
3. [Relationships and Constraints](#relationships-and-constraints)
4. [Indexes and Performance](#indexes-and-performance)
5. [Data Types and Validation](#data-types-and-validation)
6. [Migration Scripts](#migration-scripts)
7. [Performance Optimization](#performance-optimization)
8. [Backup and Maintenance](#backup-and-maintenance)

---

## Schema Overview

### Database Information
- **Database Engine**: PostgreSQL 13+
- **Character Encoding**: UTF-8
- **Collation**: en_US.UTF-8
- **Total Tables**: 4 core tables
- **Relationships**: 2 foreign key relationships
- **Storage**: Approximately 50MB per 1000 projects

### Entity Relationship Diagram
```
┌─────────────────┐    1:N    ┌─────────────────┐    1:N    ┌─────────────────┐
│     SOURCE      │ ────────▶ │  NEWS_ARTICLE   │ ────────▶ │   SCRAPE_LOG    │
│                 │           │                 │           │                 │
│ • id (PK)       │           │ • id (PK)       │           │ • id (PK)       │
│ • url (UNIQUE)  │           │ • url (UNIQUE)  │           │ • source_id(FK) │
│ • name          │           │ • source_id(FK) │           │ • timestamp     │
│ • description   │           │ • title         │           │ • status        │
│ • last_checked  │           │ • content       │           │ • message       │
│ • status        │           │ • published_date│           │ • articles_found│
│ • created_at    │           │ • is_processed  │           │ • projects_added│
└─────────────────┘           │ • created_at    │           └─────────────────┘
                              └─────────────────┘
                                       │
                                       │ (Logical)
                                       ▼
                              ┌─────────────────┐
                              │     PROJECT     │
                              │                 │
                              │ • id (PK)       │
                              │ • source (URL)  │
                              │ • name          │
                              │ • company       │
                              │ • type          │
                              │ • capacities... │
                              │ • investments.. │
                              │ • status        │
                              │ • timestamps... │
                              └─────────────────┘
```

---

## Core Tables

### 1. PROJECT Table
**Purpose**: Store comprehensive renewable energy project information

#### Schema Definition
```sql
CREATE TABLE project (
    -- Primary identifier
    id SERIAL PRIMARY KEY,
    index INTEGER,
    
    -- Project classification
    type VARCHAR(50),                    -- Solar, Battery, Wind, Hydro, Green Hydrogen, Biofuel
    name VARCHAR(200),
    company VARCHAR(200),
    ownership VARCHAR(50),               -- Public, Private, Joint Venture
    pli_status VARCHAR(50),              -- PLI, Non-PLI, Under Review
    
    -- Geographic information
    state VARCHAR(100),
    location VARCHAR(100),
    
    -- Timeline information
    announcement_date DATE,
    expected_completion VARCHAR(50),
    last_updated DATE,
    
    -- Project categorization
    category VARCHAR(50),                -- Manufacturing, Generation, Storage, Integration
    input_type VARCHAR(100),             -- Raw materials or energy source
    output_type VARCHAR(100),            -- Final product or energy type
    
    -- Capacity information (type-specific)
    -- Solar Manufacturing
    cell_capacity DOUBLE PRECISION,      -- GW
    module_capacity DOUBLE PRECISION,    -- GW
    integration_capacity DOUBLE PRECISION, -- GW
    
    -- Power Generation/Storage
    generation_capacity DOUBLE PRECISION DEFAULT 0, -- MW/GW
    storage_capacity DOUBLE PRECISION DEFAULT 0,    -- MWh/GWh
    
    -- Green Hydrogen
    electrolyzer_capacity DOUBLE PRECISION DEFAULT 0, -- MW
    hydrogen_production DOUBLE PRECISION DEFAULT 0,   -- tons per day
    
    -- Biofuel
    biofuel_capacity DOUBLE PRECISION DEFAULT 0,    -- million liters per year
    feedstock_type VARCHAR(100),                     -- sugarcane, corn, waste, etc.
    
    -- Regulatory and approval status
    status VARCHAR(50),                  -- Announced, Under Construction, Operational
    land_acquisition VARCHAR(50),        -- Completed, In Progress, Pending
    power_approval VARCHAR(50),          -- Obtained, Applied, Not Required
    environment_clearance VARCHAR(50),   -- Obtained, Applied, Pending
    almm_listing VARCHAR(50),            -- Listed, Applied, Not Applicable
    
    -- Investment information
    investment_usd DOUBLE PRECISION,     -- USD Million
    investment_inr DOUBLE PRECISION,     -- INR Billion
    
    -- Source and metadata
    source VARCHAR(500),                 -- Original news article URL
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Field Descriptions

**Core Identification**
- `id`: Auto-incrementing primary key
- `index`: Optional manual index for tracking
- `type`: Primary energy category (Solar, Battery, Wind, Hydro, Green Hydrogen, Biofuel)
- `name`: Project name as announced
- `company`: Primary company or developer

**Geographic and Ownership**
- `state`: Indian state location
- `location`: City, district, or specific location
- `ownership`: Ownership structure (Public/Private/Joint Venture)
- `pli_status`: Production Linked Incentive scheme participation

**Capacity Fields by Type**
- **Solar Manufacturing**: `cell_capacity`, `module_capacity`, `integration_capacity` (GW)
- **Power Projects**: `generation_capacity` (MW/GW), `storage_capacity` (MWh/GWh)
- **Green Hydrogen**: `electrolyzer_capacity` (MW), `hydrogen_production` (tons/day)
- **Biofuel**: `biofuel_capacity` (million liters/year), `feedstock_type`

**Investment Tracking**
- `investment_usd`: Investment amount in USD millions
- `investment_inr`: Investment amount in INR billions
- Both fields used for multi-currency announcements

### 2. SOURCE Table
**Purpose**: Manage news sources for web scraping

#### Schema Definition
```sql
CREATE TABLE source (
    id SERIAL PRIMARY KEY,
    url VARCHAR(500) UNIQUE NOT NULL,    -- Base URL for news source
    name VARCHAR(200),                   -- Human-readable source name
    description TEXT,                    -- Source description and focus
    last_checked TIMESTAMP,              -- Last successful scraping time
    status VARCHAR(50),                  -- Success, Failed, Disabled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Field Descriptions
- `url`: Base URL for the news source (must be unique)
- `name`: Display name (e.g., "Economic Times Energy")
- `description`: Editorial focus and reliability notes
- `last_checked`: Timestamp of last successful scraping operation
- `status`: Current operational status for monitoring

#### Sample Data
```sql
INSERT INTO source (url, name, description, status) VALUES
('https://energy.economictimes.indiatimes.com', 'Economic Times Energy', 'Premier business news with renewable energy focus', 'Success'),
('https://mercomindia.com', 'Mercom India', 'Specialized renewable energy industry news', 'Success'),
('https://www.pv-magazine-india.com', 'PV Magazine India', 'Solar industry news and analysis', 'Success');
```

### 3. NEWS_ARTICLE Table
**Purpose**: Track processed news articles and their content

#### Schema Definition
```sql
CREATE TABLE news_article (
    id SERIAL PRIMARY KEY,
    url VARCHAR(500) UNIQUE NOT NULL,    -- Article URL
    title VARCHAR(500),                  -- Article headline
    content TEXT,                        -- Full article text
    published_date TIMESTAMP,            -- Publication timestamp
    source_id INTEGER REFERENCES source(id), -- Foreign key to source
    is_processed BOOLEAN DEFAULT FALSE,  -- Processing status flag
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Field Descriptions
- `url`: Complete URL to the specific article (unique constraint)
- `title`: Article headline as extracted
- `content`: Full article text after cleaning
- `published_date`: Original publication date from article
- `source_id`: Foreign key reference to source table
- `is_processed`: Flag indicating whether article has been analyzed for projects

### 4. SCRAPE_LOG Table
**Purpose**: Audit trail for scraping operations and performance monitoring

#### Schema Definition
```sql
CREATE TABLE scrape_log (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES source(id), -- Foreign key to source
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50),                  -- Success, Failed, Partial
    message TEXT,                        -- Detailed status message or error
    articles_found INTEGER DEFAULT 0,    -- Number of articles discovered
    projects_added INTEGER DEFAULT 0     -- Number of new projects created
);
```

#### Field Descriptions
- `source_id`: Reference to the scraped source
- `timestamp`: Exact time of scraping operation
- `status`: Operation outcome (Success/Failed/Partial)
- `message`: Detailed information about operation or error details
- `articles_found`: Count of articles discovered in this operation
- `projects_added`: Count of new projects extracted and added

---

## Relationships and Constraints

### Foreign Key Relationships

#### news_article → source
```sql
ALTER TABLE news_article 
ADD CONSTRAINT news_article_source_id_fkey 
FOREIGN KEY (source_id) REFERENCES source(id);
```

#### scrape_log → source
```sql
ALTER TABLE scrape_log 
ADD CONSTRAINT scrape_log_source_id_fkey 
FOREIGN KEY (source_id) REFERENCES source(id);
```

### Unique Constraints

#### Source URL Uniqueness
```sql
ALTER TABLE source 
ADD CONSTRAINT source_url_key 
UNIQUE (url);
```

#### Article URL Uniqueness
```sql
ALTER TABLE news_article 
ADD CONSTRAINT news_article_url_key 
UNIQUE (url);
```

### Check Constraints

#### Investment Amount Validation
```sql
ALTER TABLE project 
ADD CONSTRAINT check_investment_positive 
CHECK (investment_usd IS NULL OR investment_usd > 0);

ALTER TABLE project 
ADD CONSTRAINT check_investment_inr_positive 
CHECK (investment_inr IS NULL OR investment_inr > 0);
```

#### Capacity Validation
```sql
ALTER TABLE project 
ADD CONSTRAINT check_capacity_positive 
CHECK (
    (cell_capacity IS NULL OR cell_capacity > 0) AND
    (module_capacity IS NULL OR module_capacity > 0) AND
    (generation_capacity IS NULL OR generation_capacity >= 0) AND
    (storage_capacity IS NULL OR storage_capacity >= 0)
);
```

#### Status Field Validation
```sql
ALTER TABLE project 
ADD CONSTRAINT check_project_status 
CHECK (status IN ('Announced', 'Under Construction', 'Operational', 'Cancelled', 'Delayed'));

ALTER TABLE project 
ADD CONSTRAINT check_pli_status 
CHECK (pli_status IN ('PLI', 'Non-PLI', 'Under Review', 'Not Applicable'));
```

---

## Indexes and Performance

### Current Indexes

#### Primary Key Indexes (Automatic)
```sql
-- Automatically created with PRIMARY KEY constraints
CREATE UNIQUE INDEX project_pkey ON project (id);
CREATE UNIQUE INDEX source_pkey ON source (id);
CREATE UNIQUE INDEX news_article_pkey ON news_article (id);
CREATE UNIQUE INDEX scrape_log_pkey ON scrape_log (id);
```

#### Unique Constraint Indexes (Automatic)
```sql
-- Automatically created with UNIQUE constraints
CREATE UNIQUE INDEX source_url_key ON source (url);
CREATE UNIQUE INDEX news_article_url_key ON news_article (url);
```

### Recommended Performance Indexes

#### Project Query Optimization
```sql
-- Type-based filtering (most common query pattern)
CREATE INDEX idx_project_type ON project(type);

-- State-based geographic queries
CREATE INDEX idx_project_state ON project(state);

-- Status filtering for pipeline analysis
CREATE INDEX idx_project_status ON project(status);

-- Date-based queries for recent projects
CREATE INDEX idx_project_announcement_date ON project(announcement_date);
CREATE INDEX idx_project_created_at ON project(created_at);

-- Company-based competitive analysis
CREATE INDEX idx_project_company ON project(company);

-- PLI scheme analysis
CREATE INDEX idx_project_pli_status ON project(pli_status);

-- Composite index for common filter combinations
CREATE INDEX idx_project_type_state ON project(type, state);
CREATE INDEX idx_project_type_status ON project(type, status);
```

#### Article Processing Optimization
```sql
-- Unprocessed articles query
CREATE INDEX idx_news_article_processed ON news_article(is_processed);

-- Source-based article retrieval
CREATE INDEX idx_news_article_source_id ON news_article(source_id);

-- Date-based article queries
CREATE INDEX idx_news_article_published_date ON news_article(published_date);
```

#### Scraping Performance Monitoring
```sql
-- Source performance analysis
CREATE INDEX idx_scrape_log_source_id ON scrape_log(source_id);

-- Time-based log analysis
CREATE INDEX idx_scrape_log_timestamp ON scrape_log(timestamp);

-- Status-based error analysis
CREATE INDEX idx_scrape_log_status ON scrape_log(status);
```

### Performance Optimization Queries

#### Index Usage Analysis
```sql
-- Check index usage statistics
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes 
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

#### Table Statistics
```sql
-- Analyze table sizes and row counts
SELECT 
    schemaname,
    tablename,
    n_tup_ins,
    n_tup_upd,
    n_tup_del,
    n_live_tup,
    n_dead_tup
FROM pg_stat_user_tables 
WHERE schemaname = 'public';
```

---

## Data Types and Validation

### Capacity Field Standards

#### Units and Precision
- **Power Capacity**: DOUBLE PRECISION for MW/GW values
- **Energy Storage**: DOUBLE PRECISION for MWh/GWh values
- **Production Rates**: DOUBLE PRECISION for tons/day, liters/year
- **Investment**: DOUBLE PRECISION for financial amounts

#### Value Ranges
```sql
-- Reasonable capacity ranges for validation
-- Solar Manufacturing: 0.1 GW to 50 GW per project
-- Battery Storage: 0.1 GWh to 100 GWh per project
-- Wind Manufacturing: 100 MW to 10 GW per project
-- Green Hydrogen: 10 MW to 1000 MW electrolyzer capacity

ALTER TABLE project ADD CONSTRAINT check_reasonable_capacity 
CHECK (
    (cell_capacity IS NULL OR (cell_capacity >= 0.01 AND cell_capacity <= 100)) AND
    (storage_capacity IS NULL OR (storage_capacity >= 0.01 AND storage_capacity <= 500)) AND
    (electrolyzer_capacity IS NULL OR (electrolyzer_capacity >= 1 AND electrolyzer_capacity <= 2000))
);
```

### String Field Standards

#### Character Limits and Validation
```sql
-- Project names: 200 characters maximum
-- Company names: 200 characters maximum
-- Locations: 100 characters maximum
-- URLs: 500 characters maximum
-- Text content: Unlimited (TEXT type)

-- Enum-like validation for key fields
ALTER TABLE project ADD CONSTRAINT check_project_type 
CHECK (type IN ('Solar', 'Battery', 'Wind', 'Hydro', 'Green Hydrogen', 'Biofuel'));

ALTER TABLE project ADD CONSTRAINT check_ownership_type 
CHECK (ownership IN ('Public', 'Private', 'Joint Venture', 'Government', 'Cooperative'));
```

### Date and Time Standards

#### Timestamp Handling
```sql
-- All timestamps in UTC
-- created_at: Auto-set on insert
-- updated_at: Auto-update on modification
-- announcement_date: Project announcement date (DATE only)
-- last_checked: Source scraping timestamp (TIMESTAMP)

-- Trigger for automatic updated_at maintenance
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_project_updated_at 
    BEFORE UPDATE ON project 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
```

---

## Migration Scripts

### Initial Schema Creation
```sql
-- Complete schema setup script
-- Execute in order for new database setup

-- 1. Create source table
CREATE TABLE source (
    id SERIAL PRIMARY KEY,
    url VARCHAR(500) UNIQUE NOT NULL,
    name VARCHAR(200),
    description TEXT,
    last_checked TIMESTAMP,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Create news_article table
CREATE TABLE news_article (
    id SERIAL PRIMARY KEY,
    url VARCHAR(500) UNIQUE NOT NULL,
    title VARCHAR(500),
    content TEXT,
    published_date TIMESTAMP,
    source_id INTEGER REFERENCES source(id),
    is_processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Create project table
CREATE TABLE project (
    id SERIAL PRIMARY KEY,
    index INTEGER,
    type VARCHAR(50),
    name VARCHAR(200),
    company VARCHAR(200),
    ownership VARCHAR(50),
    pli_status VARCHAR(50),
    state VARCHAR(100),
    location VARCHAR(100),
    announcement_date DATE,
    category VARCHAR(50),
    input_type VARCHAR(100),
    output_type VARCHAR(100),
    cell_capacity DOUBLE PRECISION,
    module_capacity DOUBLE PRECISION,
    integration_capacity DOUBLE PRECISION,
    generation_capacity DOUBLE PRECISION DEFAULT 0,
    storage_capacity DOUBLE PRECISION DEFAULT 0,
    electrolyzer_capacity DOUBLE PRECISION DEFAULT 0,
    hydrogen_production DOUBLE PRECISION DEFAULT 0,
    biofuel_capacity DOUBLE PRECISION DEFAULT 0,
    feedstock_type VARCHAR(100),
    status VARCHAR(50),
    land_acquisition VARCHAR(50),
    power_approval VARCHAR(50),
    environment_clearance VARCHAR(50),
    almm_listing VARCHAR(50),
    investment_usd DOUBLE PRECISION,
    investment_inr DOUBLE PRECISION,
    expected_completion VARCHAR(50),
    last_updated DATE,
    source VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Create scrape_log table
CREATE TABLE scrape_log (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES source(id),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50),
    message TEXT,
    articles_found INTEGER DEFAULT 0,
    projects_added INTEGER DEFAULT 0
);

-- 5. Create performance indexes
CREATE INDEX idx_project_type ON project(type);
CREATE INDEX idx_project_state ON project(state);
CREATE INDEX idx_project_status ON project(status);
CREATE INDEX idx_project_created_at ON project(created_at);
CREATE INDEX idx_news_article_processed ON news_article(is_processed);
CREATE INDEX idx_scrape_log_timestamp ON scrape_log(timestamp);
```

### Data Migration Examples
```sql
-- Migrate legacy data with new field structure
-- Example: Adding new capacity fields for existing projects

-- Step 1: Add new columns (already in current schema)
ALTER TABLE project ADD COLUMN IF NOT EXISTS generation_capacity DOUBLE PRECISION DEFAULT 0;
ALTER TABLE project ADD COLUMN IF NOT EXISTS storage_capacity DOUBLE PRECISION DEFAULT 0;

-- Step 2: Migrate existing data based on project type
UPDATE project 
SET generation_capacity = COALESCE(cell_capacity, module_capacity, 0)
WHERE type IN ('Solar', 'Wind', 'Hydro') 
AND generation_capacity = 0;

UPDATE project 
SET storage_capacity = COALESCE(cell_capacity, module_capacity, 0)
WHERE type = 'Battery' 
AND storage_capacity = 0;

-- Step 3: Verify migration
SELECT type, 
       COUNT(*) as total_projects,
       COUNT(generation_capacity) as with_generation,
       COUNT(storage_capacity) as with_storage
FROM project 
GROUP BY type;
```

---

## Performance Optimization

### Query Optimization Strategies

#### Common Query Patterns
```sql
-- 1. Project filtering by type and state (most common)
SELECT * FROM project 
WHERE type = 'Solar' AND state = 'Gujarat'
ORDER BY announcement_date DESC;

-- Optimization: Composite index
CREATE INDEX idx_project_type_state_date ON project(type, state, announcement_date);

-- 2. Recent projects across all types
SELECT * FROM project 
WHERE announcement_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY announcement_date DESC;

-- Optimization: Date index with included columns
CREATE INDEX idx_project_recent ON project(announcement_date DESC) 
WHERE announcement_date >= CURRENT_DATE - INTERVAL '1 year';

-- 3. Capacity aggregation by type
SELECT type, 
       SUM(cell_capacity) as total_cell,
       SUM(module_capacity) as total_module,
       COUNT(*) as project_count
FROM project 
WHERE status IN ('Announced', 'Under Construction')
GROUP BY type;

-- Optimization: Partial index on active projects
CREATE INDEX idx_project_active_status ON project(type, status) 
WHERE status IN ('Announced', 'Under Construction');
```

#### Materialized Views for Complex Analytics
```sql
-- Create materialized view for dashboard statistics
CREATE MATERIALIZED VIEW project_statistics AS
SELECT 
    type,
    state,
    COUNT(*) as project_count,
    SUM(COALESCE(cell_capacity, 0)) as total_cell_capacity,
    SUM(COALESCE(module_capacity, 0)) as total_module_capacity,
    SUM(COALESCE(generation_capacity, 0)) as total_generation_capacity,
    SUM(COALESCE(investment_usd, 0)) as total_investment_usd,
    AVG(COALESCE(investment_usd, 0)) as avg_investment_usd
FROM project 
WHERE status IN ('Announced', 'Under Construction', 'Operational')
GROUP BY type, state;

-- Create index on materialized view
CREATE INDEX idx_project_stats_type_state ON project_statistics(type, state);

-- Refresh schedule (daily)
-- Add to cron: 0 6 * * * psql -d renewable_db -c "REFRESH MATERIALIZED VIEW project_statistics;"
```

### Database Maintenance

#### Regular Maintenance Tasks
```sql
-- Daily maintenance (automated)
VACUUM ANALYZE project;
VACUUM ANALYZE news_article;
VACUUM ANALYZE scrape_log;

-- Weekly maintenance
REINDEX TABLE project;
UPDATE pg_stat_user_tables SET n_tup_ins = 0, n_tup_upd = 0;

-- Monthly maintenance
VACUUM FULL project;  -- Only during maintenance window
CLUSTER project USING idx_project_type_state_date;  -- Physical reordering
```

#### Statistics and Monitoring
```sql
-- Table size monitoring
SELECT 
    table_name,
    pg_size_pretty(pg_total_relation_size(table_name::text)) as size,
    pg_total_relation_size(table_name::text) as size_bytes
FROM (VALUES ('project'), ('source'), ('news_article'), ('scrape_log')) AS t(table_name);

-- Index effectiveness
SELECT 
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(pg_relation_size(indexname::text)) as index_size
FROM pg_stat_user_indexes 
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

---

## Backup and Maintenance

### Backup Strategy

#### Daily Automated Backup
```bash
#!/bin/bash
# daily_backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/renewable_energy"
BACKUP_FILE="$BACKUP_DIR/renewable_db_$DATE.sql"

# Full database backup
pg_dump -U $PGUSER -h $PGHOST -p $PGPORT $PGDATABASE > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

# Schema-only backup for quick restoration
pg_dump -U $PGUSER -h $PGHOST -p $PGPORT --schema-only $PGDATABASE > "$BACKUP_DIR/schema_$DATE.sql"

# Data-only backup for large datasets
pg_dump -U $PGUSER -h $PGHOST -p $PGPORT --data-only $PGDATABASE > "$BACKUP_DIR/data_$DATE.sql"
gzip "$BACKUP_DIR/data_$DATE.sql"

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

#### Table-Specific Backups
```sql
-- Project data export (most critical)
COPY project TO '/tmp/project_backup.csv' WITH CSV HEADER;

-- Source configuration backup
COPY source TO '/tmp/source_backup.csv' WITH CSV HEADER;

-- Recent scraping logs (last 30 days)
COPY (
    SELECT * FROM scrape_log 
    WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
) TO '/tmp/scrape_log_recent.csv' WITH CSV HEADER;
```

### Recovery Procedures

#### Complete Database Restoration
```sql
-- Drop and recreate database
DROP DATABASE IF EXISTS renewable_energy_db;
CREATE DATABASE renewable_energy_db;

-- Restore from backup
psql -U $PGUSER -h $PGHOST -p $PGPORT -d renewable_energy_db -f backup_file.sql

-- Verify restoration
SELECT COUNT(*) FROM project;
SELECT COUNT(*) FROM source;
SELECT MAX(created_at) FROM project;
```

#### Selective Table Recovery
```sql
-- Restore specific table from backup
DROP TABLE IF EXISTS project_backup;
CREATE TABLE project_backup AS SELECT * FROM project WHERE FALSE;

-- Load from CSV backup
COPY project_backup FROM '/tmp/project_backup.csv' WITH CSV HEADER;

-- Validate and replace
SELECT COUNT(*) FROM project_backup;
DROP TABLE project;
ALTER TABLE project_backup RENAME TO project;
```

This comprehensive database schema documentation provides complete technical details for understanding, maintaining, and extending the renewable energy tracking platform's data architecture.