from sqlalchemy import (
    Column, Integer, String, Text, Date, Boolean, 
    TIMESTAMP, ForeignKey, ARRAY, func, Float, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import TSVECTOR
from datetime import datetime
from typing import List, Optional

Base = declarative_base()


class Opportunity(Base):
    """Research funding and internship opportunities."""
    
    __tablename__ = "opportunities"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    description = Column(Text)
    department = Column(Text)  # Changed from String(100) to Text for longer department names
    opportunity_type = Column(String(50))  # 'funding', 'internship', 'research'
    eligibility_requirements = Column(Text)
    deadline = Column(Text)  # Changed from Date to Text to handle descriptive deadlines from LLM
    funding_amount = Column(Text)  # Changed from String(100) to Text to handle longer funding descriptions
    application_url = Column(Text)
    source_url = Column(Text, nullable=False)
    contact_email = Column(String(255))
    tags = Column(ARRAY(String))  # Store as string array for easy querying
    
    # Full-text search vector columns
    search_vector = Column(TSVECTOR)
    
    # LLM Validation and Enhancement Fields
    # LLM HTML Parsing Fields  
    llm_parsed = Column(Boolean, default=False)  # Whether this was extracted by LLM
    parsing_confidence = Column(Float)  # Confidence in the extraction quality
    llm_error = Column(Text)  # Any errors during LLM processing
    processed_at = Column(TIMESTAMP)  # When LLM processing was completed
    scraper_used = Column(String(100))  # Which scraper class was used
    
    # Opportunity Tracking Fields (NEW)
    content_hash = Column(String(64), index=True)  # SHA-256 hash of key content for similarity detection
    first_seen_at = Column(TIMESTAMP, default=func.current_timestamp())  # When first discovered
    last_seen_at = Column(TIMESTAMP, default=func.current_timestamp())  # When last found in a scrape
    last_updated_at = Column(TIMESTAMP, default=func.current_timestamp())  # When content last changed
    status = Column(String(20), default='active', index=True)  # 'new', 'active', 'missing', 'removed'
    consecutive_missing_count = Column(Integer, default=0)  # How many scrapes it's been missing
    similarity_group_id = Column(String(64))  # Group ID for similar opportunities
    
    # Metadata
    scraped_at = Column(TIMESTAMP, default=func.current_timestamp())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    notifications = relationship("NotificationSent", back_populates="opportunity")
    
    def __repr__(self):
        return f"<Opportunity(id={self.id}, title='{self.title[:50]}...', department='{self.department}')>"


class UserPreference(Base):
    """User preferences for notifications and filtering."""
    
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(200), nullable=False, unique=True, index=True)
    keywords = Column(ARRAY(String), nullable=False)
    departments = Column(ARRAY(String))
    opportunity_types = Column(ARRAY(String))
    created_at = Column(TIMESTAMP, default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, default=func.current_timestamp(), onupdate=func.current_timestamp())
    is_active = Column(Boolean, default=True)
    
    # Notification preferences
    email_notifications = Column(Boolean, default=True)
    notification_frequency = Column(String(20), default='daily')  # 'immediate', 'daily', 'weekly'
    
    # Relationships
    notifications = relationship("NotificationSent", back_populates="user")
    
    def __repr__(self):
        return f"<UserPreference(id={self.id}, email='{self.email}')>"


class NotificationSent(Base):
    """History of notifications sent to users."""
    
    __tablename__ = "notifications_sent"
    
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(200), ForeignKey('user_preferences.email'), index=True)
    opportunity_id = Column(Integer, ForeignKey('opportunities.id'), index=True)
    sent_at = Column(TIMESTAMP, default=func.current_timestamp())
    notification_type = Column(String(50), default='email')  # 'email', 'push', 'sms'
    status = Column(String(20), default='sent')  # 'sent', 'failed', 'pending'
    
    # Relationships
    user = relationship("UserPreference", back_populates="notifications")
    opportunity = relationship("Opportunity", back_populates="notifications")
    
    def __repr__(self):
        return f"<NotificationSent(id={self.id}, user_email='{self.user_email}', opportunity_id={self.opportunity_id})>"


class ScrapingLog(Base):
    """Log of scraping activities for monitoring and debugging."""
    
    __tablename__ = "scraping_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    source_url = Column(Text, nullable=False)
    scraping_started_at = Column(TIMESTAMP, default=func.current_timestamp())
    scraping_completed_at = Column(TIMESTAMP)
    status = Column(String(20), default='running')  # 'running', 'completed', 'failed'
    opportunities_found = Column(Integer, default=0)
    opportunities_new = Column(Integer, default=0)
    opportunities_updated = Column(Integer, default=0)
    error_message = Column(Text)
    
    def __repr__(self):
        return f"<ScrapingLog(id={self.id}, source_url='{self.source_url}', status='{self.status}')>"


class SearchQuery(Base):
    """Log of user search queries for analytics and improvement."""
    
    __tablename__ = "search_queries"
    
    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(Text, nullable=False)
    user_ip = Column(String(45))  # IPv6 support
    search_timestamp = Column(TIMESTAMP, default=func.current_timestamp())
    results_count = Column(Integer)
    filters_applied = Column(Text)  # JSON string of applied filters
    
    def __repr__(self):
        return f"<SearchQuery(id={self.id}, query='{self.query_text[:50]}...')>" 