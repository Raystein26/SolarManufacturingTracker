# Deployment and Operations Guide
## India Renewable Energy Infrastructure Intelligence Platform

### Production Deployment and Maintenance

---

## Table of Contents
1. [Production Environment Setup](#production-environment-setup)
2. [Database Configuration](#database-configuration)
3. [Application Deployment](#application-deployment)
4. [Monitoring and Alerting](#monitoring-and-alerting)
5. [Backup and Recovery](#backup-and-recovery)
6. [Scaling Considerations](#scaling-considerations)
7. [Security Configuration](#security-configuration)
8. [Troubleshooting Guide](#troubleshooting-guide)

---

## Production Environment Setup

### Infrastructure Requirements

#### Minimum Server Specifications
- **CPU**: 2 cores (4 cores recommended)
- **RAM**: 4GB (8GB recommended)
- **Storage**: 50GB SSD (100GB recommended)
- **Network**: 100 Mbps bandwidth
- **OS**: Ubuntu 20.04 LTS or equivalent

#### Recommended Production Stack
```bash
# Operating System
Ubuntu 20.04 LTS

# Web Server
Nginx 1.18+ (reverse proxy)
Gunicorn 23.0+ (WSGI server)

# Database
PostgreSQL 13+ with 10GB+ storage

# Process Management
systemd (service management)
supervisor (optional backup process manager)

# SSL/TLS
Let's Encrypt or commercial certificate
```

### Environment Variables
```bash
# Application Configuration
export FLASK_ENV=production
export FLASK_DEBUG=False
export DATABASE_URL=postgresql://user:password@localhost:5432/renewable_db
export SESSION_SECRET=your-secure-random-secret-key

# Optional Features
export OPENAI_API_KEY=sk-your-openai-api-key

# Performance Tuning
export SQLALCHEMY_POOL_SIZE=10
export SQLALCHEMY_MAX_OVERFLOW=20
export SQLALCHEMY_POOL_RECYCLE=300
```

---

## Database Configuration

### PostgreSQL Setup
```sql
-- Create database and user
CREATE DATABASE renewable_energy_db;
CREATE USER renewable_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE renewable_energy_db TO renewable_user;

-- Performance optimizations
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
SELECT pg_reload_conf();
```

### Database Initialization
```bash
# Initialize database schema
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Create initial data sources
python -c "
from app import app, db
from project_tracker import initialize_sources
app.app_context().push()
initialize_sources()
"
```

### Backup Configuration
```bash
#!/bin/bash
# backup_db.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/renewable_energy"
BACKUP_FILE="$BACKUP_DIR/renewable_db_$DATE.sql"

mkdir -p $BACKUP_DIR
pg_dump -U renewable_user -h localhost renewable_energy_db > $BACKUP_FILE
gzip $BACKUP_FILE

# Keep only last 30 days of backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

# Crontab entry for daily backups at 2 AM
# 0 2 * * * /path/to/backup_db.sh
```

---

## Application Deployment

### Gunicorn Configuration
```python
# gunicorn.conf.py
bind = "0.0.0.0:5000"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
preload_app = True
pidfile = "/var/run/gunicorn/renewable_energy.pid"
user = "www-data"
group = "www-data"
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
loglevel = "info"
```

### Systemd Service Configuration
```ini
# /etc/systemd/system/renewable-energy.service
[Unit]
Description=Renewable Energy Intelligence Platform
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/renewable-energy
Environment=PATH=/opt/renewable-energy/venv/bin
ExecStart=/opt/renewable-energy/venv/bin/gunicorn -c gunicorn.conf.py main:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Nginx Configuration
```nginx
# /etc/nginx/sites-available/renewable-energy
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/ssl/certificate.pem;
    ssl_certificate_key /path/to/ssl/private.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    client_max_body_size 50M;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }

    location /static/ {
        alias /opt/renewable-energy/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
}
```

### Background Services
```ini
# /etc/systemd/system/renewable-scheduler.service
[Unit]
Description=Renewable Energy Scheduler
After=network.target postgresql.service renewable-energy.service
Requires=postgresql.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/renewable-energy
Environment=PATH=/opt/renewable-energy/venv/bin
ExecStart=/opt/renewable-energy/venv/bin/python scheduler.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

### Deployment Script
```bash
#!/bin/bash
# deploy.sh
set -e

DEPLOY_DIR="/opt/renewable-energy"
BACKUP_DIR="/var/backups/renewable_energy/deployments"
DATE=$(date +%Y%m%d_%H%M%S)

echo "Starting deployment at $DATE"

# Create backup of current deployment
mkdir -p $BACKUP_DIR
tar -czf "$BACKUP_DIR/deployment_backup_$DATE.tar.gz" -C $DEPLOY_DIR .

# Stop services
sudo systemctl stop renewable-energy
sudo systemctl stop renewable-scheduler

# Update code
cd $DEPLOY_DIR
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run database migrations (if any)
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# Restart services
sudo systemctl start renewable-energy
sudo systemctl start renewable-scheduler

# Verify deployment
sleep 10
curl -f http://localhost:5000/api/projects || {
    echo "Deployment verification failed"
    # Rollback logic here
    exit 1
}

echo "Deployment completed successfully"
```

---

## Monitoring and Alerting

### Application Monitoring
```python
# monitoring.py
import psutil
import logging
from app import db
from models import Project, Source

def check_system_health():
    """Comprehensive system health check"""
    health_status = {
        'database': False,
        'memory_usage': 0,
        'cpu_usage': 0,
        'disk_usage': 0,
        'recent_projects': 0,
        'active_sources': 0
    }
    
    # Database connectivity
    try:
        db.session.execute('SELECT 1')
        health_status['database'] = True
        
        # Recent project count (last 24 hours)
        from datetime import datetime, timedelta
        yesterday = datetime.now() - timedelta(days=1)
        health_status['recent_projects'] = Project.query.filter(
            Project.created_at >= yesterday
        ).count()
        
        # Active sources
        health_status['active_sources'] = Source.query.filter_by(
            status='Success'
        ).count()
        
    except Exception as e:
        logging.error(f"Database health check failed: {e}")
    
    # System resources
    health_status['memory_usage'] = psutil.virtual_memory().percent
    health_status['cpu_usage'] = psutil.cpu_percent(interval=1)
    health_status['disk_usage'] = psutil.disk_usage('/').percent
    
    return health_status

def generate_alert(health_status):
    """Generate alerts based on health status"""
    alerts = []
    
    if not health_status['database']:
        alerts.append("CRITICAL: Database connection failed")
    
    if health_status['memory_usage'] > 90:
        alerts.append(f"WARNING: High memory usage: {health_status['memory_usage']}%")
    
    if health_status['cpu_usage'] > 90:
        alerts.append(f"WARNING: High CPU usage: {health_status['cpu_usage']}%")
    
    if health_status['disk_usage'] > 85:
        alerts.append(f"WARNING: High disk usage: {health_status['disk_usage']}%")
    
    if health_status['recent_projects'] == 0:
        alerts.append("WARNING: No new projects in last 24 hours")
    
    return alerts
```

### Log Monitoring
```bash
# /etc/logrotate.d/renewable-energy
/var/log/gunicorn/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    sharedscripts
    postrotate
        systemctl reload renewable-energy
    endscript
}

/opt/renewable-energy/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
}
```

### Performance Monitoring Script
```bash
#!/bin/bash
# monitor_performance.sh
LOG_FILE="/var/log/renewable-energy/performance.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Database connection count
DB_CONNECTIONS=$(sudo -u postgres psql -d renewable_energy_db -t -c "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';")

# Application response time
RESPONSE_TIME=$(curl -w "%{time_total}" -s -o /dev/null http://localhost:5000/api/projects)

# Memory usage
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.2f", $3/$2 * 100.0}')

# Disk usage
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')

echo "$DATE,DB_CONN:$DB_CONNECTIONS,RESPONSE:$RESPONSE_TIME,MEM:$MEMORY_USAGE%,DISK:$DISK_USAGE%" >> $LOG_FILE

# Alert if response time > 5 seconds
if (( $(echo "$RESPONSE_TIME > 5" | bc -l) )); then
    echo "ALERT: High response time: $RESPONSE_TIME seconds" | logger -t renewable-energy
fi
```

---

## Backup and Recovery

### Automated Backup Strategy
```bash
#!/bin/bash
# comprehensive_backup.sh
BACKUP_BASE="/var/backups/renewable_energy"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Database backup
pg_dump -U renewable_user renewable_energy_db | gzip > "$BACKUP_BASE/db/db_backup_$DATE.sql.gz"

# Application files backup
tar -czf "$BACKUP_BASE/app/app_backup_$DATE.tar.gz" -C /opt renewable-energy --exclude=venv --exclude=__pycache__

# Configuration backup
tar -czf "$BACKUP_BASE/config/config_backup_$DATE.tar.gz" \
    /etc/nginx/sites-available/renewable-energy \
    /etc/systemd/system/renewable-energy.service \
    /etc/systemd/system/renewable-scheduler.service

# Clean old backups
find "$BACKUP_BASE" -name "*backup*.gz" -mtime +$RETENTION_DAYS -delete

# Verify backup integrity
gunzip -t "$BACKUP_BASE/db/db_backup_$DATE.sql.gz" && echo "Database backup verified" || echo "Database backup corrupted"
```

### Recovery Procedures
```bash
#!/bin/bash
# recovery.sh
BACKUP_DATE=$1

if [ -z "$BACKUP_DATE" ]; then
    echo "Usage: $0 YYYYMMDD_HHMMSS"
    exit 1
fi

BACKUP_BASE="/var/backups/renewable_energy"

echo "Starting recovery for backup: $BACKUP_DATE"

# Stop services
sudo systemctl stop renewable-energy
sudo systemctl stop renewable-scheduler

# Restore database
echo "Restoring database..."
sudo -u postgres dropdb renewable_energy_db
sudo -u postgres createdb renewable_energy_db
gunzip -c "$BACKUP_BASE/db/db_backup_$BACKUP_DATE.sql.gz" | sudo -u postgres psql renewable_energy_db

# Restore application files
echo "Restoring application files..."
cd /opt
tar -xzf "$BACKUP_BASE/app/app_backup_$BACKUP_DATE.tar.gz"

# Restore configuration
echo "Restoring configuration..."
tar -xzf "$BACKUP_BASE/config/config_backup_$BACKUP_DATE.tar.gz" -C /

# Restart services
sudo systemctl start renewable-energy
sudo systemctl start renewable-scheduler

echo "Recovery completed"
```

---

## Scaling Considerations

### Horizontal Scaling
```python
# Load balancer configuration for multiple app servers
# /etc/nginx/conf.d/renewable-upstream.conf
upstream renewable_app {
    server 10.0.1.10:5000 weight=1 max_fails=3 fail_timeout=30s;
    server 10.0.1.11:5000 weight=1 max_fails=3 fail_timeout=30s;
    server 10.0.1.12:5000 weight=1 max_fails=3 fail_timeout=30s;
}

server {
    location / {
        proxy_pass http://renewable_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Database Scaling
```sql
-- Read replica configuration
-- Master database settings
ALTER SYSTEM SET wal_level = 'replica';
ALTER SYSTEM SET max_wal_senders = 3;
ALTER SYSTEM SET wal_keep_segments = 32;
SELECT pg_reload_conf();

-- Create replication user
CREATE USER replicator REPLICATION LOGIN CONNECTION LIMIT 1 ENCRYPTED PASSWORD 'replica_password';
```

### Caching Layer
```python
# Redis caching implementation
import redis
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_result(expiration=300):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_result = redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            redis_client.setex(cache_key, expiration, json.dumps(result))
            return result
        return wrapper
    return decorator

@cache_result(expiration=600)
def get_project_statistics():
    # Expensive database query
    pass
```

---

## Security Configuration

### SSL/TLS Setup
```bash
# Let's Encrypt certificate installation
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# Auto-renewal setup
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
```

### Firewall Configuration
```bash
# UFW firewall setup
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable

# Application-specific rules
sudo ufw allow from 10.0.0.0/8 to any port 5432  # Database access from internal network
```

### Security Headers
```nginx
# Additional security headers in Nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net";
add_header Referrer-Policy "strict-origin-when-cross-origin";
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()";
```

---

## Troubleshooting Guide

### Common Issues and Solutions

#### High Memory Usage
```bash
# Identify memory-consuming processes
ps aux --sort=-%mem | head -20

# Check for memory leaks in application
sudo -u www-data python -c "
import psutil
process = psutil.Process()
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"

# Solution: Restart application services
sudo systemctl restart renewable-energy
```

#### Database Connection Issues
```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';

-- Check for long-running queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';

-- Kill problematic queries
SELECT pg_terminate_backend(pid) WHERE condition;
```

#### Scraping Failures
```python
# Debug scraping issues
def diagnose_scraping():
    from models import Source, ScrapeLog
    
    # Check recent failures
    failed_sources = Source.query.filter_by(status='Failed').all()
    for source in failed_sources:
        latest_log = ScrapeLog.query.filter_by(source_id=source.id)\
                                   .order_by(ScrapeLog.timestamp.desc())\
                                   .first()
        print(f"Source: {source.name}, Error: {latest_log.message}")
```

#### Performance Degradation
```bash
# Database performance analysis
sudo -u postgres psql renewable_energy_db -c "
SELECT schemaname, tablename, seq_scan, seq_tup_read, idx_scan, idx_tup_fetch
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan;
"

# Check for missing indexes
sudo -u postgres psql renewable_energy_db -c "
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE tablename = 'project' AND n_distinct > 100;
"
```

### Emergency Procedures

#### Complete System Recovery
```bash
#!/bin/bash
# emergency_recovery.sh
echo "Starting emergency recovery procedure"

# Stop all services
sudo systemctl stop renewable-energy
sudo systemctl stop renewable-scheduler
sudo systemctl stop nginx

# Check system resources
df -h
free -h
systemctl status postgresql

# Restore from latest backup
LATEST_BACKUP=$(ls -t /var/backups/renewable_energy/db/ | head -1)
echo "Restoring from: $LATEST_BACKUP"

# Execute recovery
sudo -u postgres dropdb renewable_energy_db
sudo -u postgres createdb renewable_energy_db
gunzip -c "/var/backups/renewable_energy/db/$LATEST_BACKUP" | sudo -u postgres psql renewable_energy_db

# Restart services
sudo systemctl start postgresql
sudo systemctl start renewable-energy
sudo systemctl start renewable-scheduler
sudo systemctl start nginx

# Verify recovery
curl -f http://localhost/api/projects && echo "Recovery successful" || echo "Recovery failed"
```

This deployment guide provides comprehensive instructions for production deployment, monitoring, and maintenance of the renewable energy tracking platform. Regular review and updates ensure optimal system performance and reliability.