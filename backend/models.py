"""
Flask-SQLAlchemy models for Stanford Research Opportunities
Converted from FastAPI SQLAlchemy models
"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, ARRAY, String, Text, Float, JSON, TIMESTAMP, Boolean, Integer, Date
from sqlalchemy.dialects.postgresql import TSVECTOR
from datetime import datetime
from typing import List, Optional

db = SQLAlchemy()


class Opportunity(db.Model):
    """Research funding and internship opportunities."""
    
    __tablename__ = "opportunities"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    department = db.Column(db.Text)
    opportunity_type = db.Column(db.String(50))  # 'funding', 'internship', 'research'
    eligibility_requirements = db.Column(db.Text)
    deadline = db.Column(db.Text)  # Text to handle descriptive deadlines
    funding_amount = db.Column(db.Text)
    application_url = db.Column(db.Text)
    source_url = db.Column(db.Text, nullable=False)
    contact_email = db.Column(db.String(255))
    tags = db.Column(ARRAY(String))  # Store as string array
    
    # Full-text search vector columns
    search_vector = db.Column(TSVECTOR)
    
    # LLM Validation and Enhancement Fields
    llm_parsed = db.Column(db.Boolean, default=False)
    parsing_confidence = db.Column(db.Float)
    llm_error = db.Column(db.Text)
    processed_at = db.Column(TIMESTAMP)
    scraper_used = db.Column(db.String(100))
    
    # Opportunity Tracking Fields (NEW)
    content_hash = db.Column(db.String(64), index=True)  # SHA-256 hash of key content for similarity detection
    first_seen_at = db.Column(TIMESTAMP, default=func.current_timestamp())  # When first discovered
    last_seen_at = db.Column(TIMESTAMP, default=func.current_timestamp())  # When last found in a scrape
    last_updated_at = db.Column(TIMESTAMP, default=func.current_timestamp())  # When content last changed
    status = db.Column(db.String(20), default='active', index=True)  # 'new', 'active', 'missing', 'removed'
    consecutive_missing_count = db.Column(db.Integer, default=0)  # How many scrapes it's been missing
    similarity_group_id = db.Column(db.String(64))  # Group ID for similar opportunities
    
    # Metadata
    scraped_at = db.Column(TIMESTAMP, default=func.current_timestamp())
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    notifications = db.relationship("NotificationSent", back_populates="opportunity")
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'department': self.department,
            'opportunity_type': self.opportunity_type,
            'eligibility_requirements': self.eligibility_requirements,
            'deadline': self.deadline,
            'funding_amount': self.funding_amount,
            'application_url': self.application_url,
            'source_url': self.source_url,
            'contact_email': self.contact_email,
            'tags': self.tags or [],
            'llm_parsed': self.llm_parsed,
            'parsing_confidence': self.parsing_confidence,
            'llm_error': self.llm_error,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None,
            'scraper_used': self.scraper_used,
            'scraped_at': self.scraped_at.isoformat() if self.scraped_at else None,
            'is_active': self.is_active,
            # NEW tracking fields
            'content_hash': self.content_hash,
            'first_seen_at': self.first_seen_at.isoformat() if self.first_seen_at else None,
            'last_seen_at': self.last_seen_at.isoformat() if self.last_seen_at else None,
            'last_updated_at': self.last_updated_at.isoformat() if self.last_updated_at else None,
            'status': self.status,
            'consecutive_missing_count': self.consecutive_missing_count,
            'similarity_group_id': self.similarity_group_id
        }
    
    def __repr__(self):
        return f"<Opportunity(id={self.id}, title='{self.title[:50]}...', department='{self.department}')>"


class UserPreference(db.Model):
    """User preferences for notifications and filtering."""
    
    __tablename__ = "user_preferences"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    email = db.Column(db.String(200), nullable=False, unique=True, index=True)
    keywords = db.Column(ARRAY(String), nullable=False)
    departments = db.Column(ARRAY(String))
    opportunity_types = db.Column(ARRAY(String))
    created_at = db.Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = db.Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    is_active = db.Column(db.Boolean, default=True)
    
    # Notification preferences
    email_notifications = db.Column(db.Boolean, default=True)
    notification_frequency = db.Column(db.String(20), default='daily')
    
    # Relationships
    notifications = db.relationship("NotificationSent", back_populates="user")
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'email': self.email,
            'keywords': self.keywords or [],
            'departments': self.departments or [],
            'opportunity_types': self.opportunity_types or [],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'email_notifications': self.email_notifications,
            'notification_frequency': self.notification_frequency
        }
    
    def __repr__(self):
        return f"<UserPreference(id={self.id}, email='{self.email}')>"


class NotificationSent(db.Model):
    """History of notifications sent to users."""
    
    __tablename__ = "notifications_sent"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    user_email = db.Column(db.String(200), db.ForeignKey('user_preferences.email'), index=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), index=True)
    sent_at = db.Column(TIMESTAMP, default=func.current_timestamp())
    notification_type = db.Column(db.String(50), default='email')
    status = db.Column(db.String(20), default='sent')
    
    # Relationships
    user = db.relationship("UserPreference", back_populates="notifications")
    opportunity = db.relationship("Opportunity", back_populates="notifications")
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'user_email': self.user_email,
            'opportunity_id': self.opportunity_id,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'notification_type': self.notification_type,
            'status': self.status
        }
    
    def __repr__(self):
        return f"<NotificationSent(id={self.id}, user_email='{self.user_email}', opportunity_id={self.opportunity_id})>"


class ScrapingLog(db.Model):
    """Log of scraping activities for monitoring and debugging."""
    
    __tablename__ = "scraping_logs"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    source_url = db.Column(db.Text, nullable=False)
    scraping_started_at = db.Column(TIMESTAMP, default=func.current_timestamp())
    scraping_completed_at = db.Column(TIMESTAMP)
    status = db.Column(db.String(20), default='running')
    opportunities_found = db.Column(db.Integer, default=0)
    opportunities_new = db.Column(db.Integer, default=0)
    opportunities_updated = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'source_url': self.source_url,
            'scraping_started_at': self.scraping_started_at.isoformat() if self.scraping_started_at else None,
            'scraping_completed_at': self.scraping_completed_at.isoformat() if self.scraping_completed_at else None,
            'status': self.status,
            'opportunities_found': self.opportunities_found,
            'opportunities_new': self.opportunities_new,
            'opportunities_updated': self.opportunities_updated,
            'error_message': self.error_message
        }
    
    def __repr__(self):
        return f"<ScrapingLog(id={self.id}, source_url='{self.source_url}', status='{self.status}')>"


class SearchQuery(db.Model):
    """Log of user search queries for analytics and improvement."""
    
    __tablename__ = "search_queries"
    
    id = db.Column(db.Integer, primary_key=True, index=True)
    query_text = db.Column(db.Text, nullable=False)
    user_ip = db.Column(db.String(45))  # IPv6 support
    search_timestamp = db.Column(TIMESTAMP, default=func.current_timestamp())
    results_count = db.Column(db.Integer)
    filters_applied = db.Column(db.Text)  # JSON string of applied filters
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'query_text': self.query_text,
            'user_ip': self.user_ip,
            'search_timestamp': self.search_timestamp.isoformat() if self.search_timestamp else None,
            'results_count': self.results_count,
            'filters_applied': self.filters_applied
        }
    
    def __repr__(self):
        return f"<SearchQuery(id={self.id}, query='{self.query_text[:50]}...')>" 