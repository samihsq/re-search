from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from enum import Enum


class OpportunityType(str, Enum):
    """Enum for opportunity types."""
    funding = "funding"
    internship = "internship"
    research = "research"
    fellowship = "fellowship"
    leadership = "leadership"


class NotificationFrequency(str, Enum):
    """Enum for notification frequencies."""
    immediate = "immediate"
    daily = "daily"
    weekly = "weekly"


# Base schemas
class OpportunityBase(BaseModel):
    """Base schema for Opportunity."""
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    department: Optional[str] = Field(None, max_length=200)
    opportunity_type: OpportunityType
    eligibility_requirements: Optional[str] = None
    deadline: Optional[str] = None  # Changed from date to str to handle descriptive deadlines
    funding_amount: Optional[str] = None  # Removed max_length constraint since changed to TEXT
    application_url: Optional[str] = None
    source_url: str
    contact_email: Optional[str] = Field(None, max_length=200)
    tags: Optional[List[str]] = []


class OpportunityCreate(OpportunityBase):
    """Schema for creating opportunities."""
    pass


class OpportunityUpdate(BaseModel):
    """Schema for updating opportunities."""
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    department: Optional[str] = Field(None, max_length=200)
    opportunity_type: Optional[OpportunityType] = None
    eligibility_requirements: Optional[str] = None
    deadline: Optional[str] = None  # Changed from date to str to handle descriptive deadlines
    funding_amount: Optional[str] = None  # Removed max_length constraint since changed to TEXT
    application_url: Optional[str] = None
    contact_email: Optional[str] = Field(None, max_length=200)
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class Opportunity(OpportunityBase):
    """Schema for returning opportunities."""
    id: int
    scraped_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


# User preference schemas
class UserPreferenceBase(BaseModel):
    """Base schema for user preferences."""
    email: EmailStr
    keywords: List[str] = Field(..., min_items=1)
    departments: Optional[List[str]] = []
    opportunity_types: Optional[List[OpportunityType]] = []
    email_notifications: bool = True
    notification_frequency: NotificationFrequency = NotificationFrequency.daily


class UserPreferenceCreate(UserPreferenceBase):
    """Schema for creating user preferences."""
    pass


class UserPreferenceUpdate(BaseModel):
    """Schema for updating user preferences."""
    keywords: Optional[List[str]] = None
    departments: Optional[List[str]] = None
    opportunity_types: Optional[List[OpportunityType]] = None
    email_notifications: Optional[bool] = None
    notification_frequency: Optional[NotificationFrequency] = None
    is_active: Optional[bool] = None


class UserPreference(UserPreferenceBase):
    """Schema for returning user preferences."""
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


# Search schemas
class SearchFilters(BaseModel):
    """Schema for search filters."""
    departments: Optional[List[str]] = []
    opportunity_types: Optional[List[OpportunityType]] = []
    deadline_from: Optional[str] = None  # Changed from date to str
    deadline_to: Optional[str] = None  # Changed from date to str
    has_funding: Optional[bool] = None
    keywords: Optional[List[str]] = []


class SearchRequest(BaseModel):
    """Schema for search requests."""
    query: Optional[str] = Field(None, description="Natural language search query")
    filters: Optional[SearchFilters] = None
    limit: int = Field(20, ge=1, le=10000, description="Number of opportunities to return (increased from 100)")
    offset: int = Field(0, ge=0)
    sort_by: Optional[str] = Field("scraped_at", description="Field to sort by")
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$")


class SearchResponse(BaseModel):
    """Schema for search responses."""
    opportunities: List[Opportunity]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool
    query_info: Optional[Dict[str, Any]] = None


# Notification schemas
class NotificationBase(BaseModel):
    """Base schema for notifications."""
    user_email: EmailStr
    opportunity_id: int
    notification_type: str = "email"


class NotificationCreate(NotificationBase):
    """Schema for creating notifications."""
    pass


class Notification(NotificationBase):
    """Schema for returning notifications."""
    id: int
    sent_at: datetime
    status: str
    
    class Config:
        from_attributes = True


# Scraping schemas
class ScrapingLogBase(BaseModel):
    """Base schema for scraping logs."""
    source_url: str
    status: str
    opportunities_found: int = 0
    opportunities_new: int = 0
    opportunities_updated: int = 0
    error_message: Optional[str] = None


class ScrapingLog(ScrapingLogBase):
    """Schema for returning scraping logs."""
    id: int
    scraping_started_at: datetime
    scraping_completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ScrapingRequest(BaseModel):
    """Schema for manual scraping requests."""
    urls: Optional[List[str]] = None  # If None, scrape all configured URLs
    force: bool = False  # Force scraping even if recently scraped


class ScrapingResponse(BaseModel):
    """Schema for scraping operation responses."""
    message: str
    results: List[Dict[str, Any]]
    total_new: int = 0
    total_updated: int = 0
    total_failed: int = 0
    metadata: Optional[Dict[str, Any]] = None  # For LLM stats and other metadata


# Analytics schemas
class OpportunityStats(BaseModel):
    """Schema for opportunity statistics."""
    total_opportunities: int
    active_opportunities: int
    opportunities_by_type: Dict[str, int]
    opportunities_by_department: Dict[str, int]
    recent_opportunities: int  # Last 7 days
    upcoming_deadlines: int  # Next 30 days


class ScrapingStats(BaseModel):
    """Schema for scraping statistics."""
    total_opportunities: int
    active_opportunities: int
    opportunities_by_type: Dict[str, int]
    recent_scraping_runs: int
    successful_scrapes: int
    failed_scrapes: int
    last_scrape_time: Optional[datetime]


# Department and meta schemas
class DepartmentInfo(BaseModel):
    """Schema for department information."""
    name: str
    opportunity_count: int
    recent_opportunities: int


class OpportunityTypeInfo(BaseModel):
    """Schema for opportunity type information."""
    type: OpportunityType
    count: int
    description: str


class HealthCheck(BaseModel):
    """Schema for health check responses."""
    status: str
    timestamp: str
    version: str
    database: str
    checks: Dict[str, Any]


# Error schemas
class ErrorResponse(BaseModel):
    """Schema for error responses."""
    error: str
    status_code: int
    detail: Optional[str] = None
    timestamp: Optional[datetime] = None


class ValidationError(BaseModel):
    """Schema for validation error responses."""
    error: str = "Validation Error"
    status_code: int = 422
    details: List[Dict[str, Any]]


# Pagination helper
class PaginationParams(BaseModel):
    """Schema for pagination parameters."""
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(20, ge=1, le=10000, description="Number of items per page (increased limit)")
    
    @property
    def offset(self) -> int:
        """Calculate offset from page and page_size."""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Return page_size as limit."""
        return self.page_size 