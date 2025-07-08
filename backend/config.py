"""
Configuration settings for Flask application
Converted from FastAPI pydantic settings
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Settings:
    """Application settings."""
    
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:password@localhost:5432/stanford_opportunities"
    )
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # Debug mode
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # API Keys
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
    scraping_api_key: Optional[str] = os.getenv("SCRAPING_API_KEY")
    
    # Redis for caching and background tasks
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Email settings
    sendgrid_api_key: Optional[str] = os.getenv("SENDGRID_API_KEY")
    from_email: str = os.getenv("FROM_EMAIL", "noreply@stanfordresearch.com")
    
    # CORS settings
    allowed_origins: str = os.getenv("ALLOWED_ORIGINS", "")
    
    # LLM settings
    enable_llm_parsing: bool = os.getenv("ENABLE_LLM_PARSING", "true").lower() == "true"
    llm_timeout: int = int(os.getenv("LLM_TIMEOUT", "45"))
    
    # Scraping settings
    max_concurrent_requests: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "5"))
    request_delay: float = float(os.getenv("REQUEST_DELAY", "1.0"))
    
    # Pagination settings
    default_page_size: int = int(os.getenv("DEFAULT_PAGE_SIZE", "20"))
    max_page_size: int = int(os.getenv("MAX_PAGE_SIZE", "10000"))
    
    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    stage: str = os.getenv("STAGE", "dev")

def get_settings() -> Settings:
    """Get application settings."""
    return Settings() 