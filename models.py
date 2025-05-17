from datetime import datetime
from app import db

class Project(db.Model):
    """Model for storing project information for all renewable energy categories"""
    id = db.Column(db.Integer, primary_key=True)
    index = db.Column(db.Integer)
    type = db.Column(db.String(50))  # Solar, Battery, Wind, Hydro, Green Hydrogen, etc.
    name = db.Column(db.String(200))
    company = db.Column(db.String(200))
    ownership = db.Column(db.String(50))
    pli_status = db.Column(db.String(50))  # "PLI" or "Non-PLI"
    state = db.Column(db.String(100))
    location = db.Column(db.String(100))
    announcement_date = db.Column(db.Date)
    category = db.Column(db.String(50))  # Manufacturing, Generation, Storage, etc.
    input_type = db.Column(db.String(100))
    output_type = db.Column(db.String(100))
    
    # Common capacity fields (used by multiple renewable types)
    generation_capacity = db.Column(db.Float)  # GW, MW for power generation
    storage_capacity = db.Column(db.Float)  # GWh, MWh for energy storage
    
    # Solar/Battery specific capacity fields
    cell_capacity = db.Column(db.Float)  # GW or GWh
    module_capacity = db.Column(db.Float)  # GW or GWh
    integration_capacity = db.Column(db.Float)  # GW or GWh
    
    # Green Hydrogen specific fields
    electrolyzer_capacity = db.Column(db.Float)  # MW
    hydrogen_production = db.Column(db.Float)  # tons per day/year
    
    # Ethanol/Biogas specific fields
    biofuel_capacity = db.Column(db.Float)  # million liters per year
    feedstock_type = db.Column(db.String(100))  # sugarcane, corn, agricultural waste, etc.
    
    # General project status
    status = db.Column(db.String(50))
    land_acquisition = db.Column(db.String(50))
    power_approval = db.Column(db.String(50))
    environment_clearance = db.Column(db.String(50))
    almm_listing = db.Column(db.String(50))  # Applicable mainly for solar
    
    # Financial information
    investment_usd = db.Column(db.Float)  # USD Million
    investment_inr = db.Column(db.Float)  # INR Billion
    
    expected_completion = db.Column(db.String(50))
    last_updated = db.Column(db.Date)
    source = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Project {self.name} ({self.type}) by {self.company}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'index': self.index,
            'type': self.type,
            'name': self.name,
            'company': self.company,
            'ownership': self.ownership,
            'pli_status': self.pli_status,
            'state': self.state,
            'location': self.location,
            'announcement_date': self.announcement_date.strftime('%d-%m-%Y') if self.announcement_date else None,
            'category': self.category,
            'input_type': self.input_type,
            'output_type': self.output_type,
            
            # Common capacity fields
            'generation_capacity': self.generation_capacity,
            'storage_capacity': self.storage_capacity,
            
            # Solar/Battery specific capacity fields
            'cell_capacity': self.cell_capacity,
            'module_capacity': self.module_capacity,
            'integration_capacity': self.integration_capacity,
            
            # Green Hydrogen specific fields
            'electrolyzer_capacity': self.electrolyzer_capacity,
            'hydrogen_production': self.hydrogen_production,
            
            # Biofuel specific fields
            'biofuel_capacity': self.biofuel_capacity,
            'feedstock_type': self.feedstock_type,
            
            # Status fields
            'status': self.status,
            'land_acquisition': self.land_acquisition,
            'power_approval': self.power_approval,
            'environment_clearance': self.environment_clearance,
            'almm_listing': self.almm_listing,
            
            # Financial information
            'investment_usd': self.investment_usd,
            'investment_inr': self.investment_inr,
            'expected_completion': self.expected_completion,
            'last_updated': self.last_updated.strftime('%d-%m-%Y') if self.last_updated else None,
            'source': self.source
        }


class Source(db.Model):
    """Model for storing information about news sources"""
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), unique=True, nullable=False)
    name = db.Column(db.String(200))
    description = db.Column(db.Text)
    last_checked = db.Column(db.DateTime)
    status = db.Column(db.String(50))  # Success, Failed, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Source {self.name} ({self.url})>'


class NewsArticle(db.Model):
    """Model for storing processed news articles"""
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), unique=True, nullable=False)
    title = db.Column(db.String(500))
    content = db.Column(db.Text)
    published_date = db.Column(db.DateTime)
    source_id = db.Column(db.Integer, db.ForeignKey('source.id'))
    source = db.relationship('Source', backref=db.backref('articles', lazy=True))
    is_processed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<NewsArticle {self.title}>'


class ScrapeLog(db.Model):
    """Model for logging scraping activities"""
    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey('source.id'))
    source = db.relationship('Source', backref=db.backref('logs', lazy=True))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50))  # Success, Failed, etc.
    message = db.Column(db.Text)
    articles_found = db.Column(db.Integer, default=0)
    projects_added = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<ScrapeLog {self.source.name if self.source else "Unknown"} {self.timestamp}>'
