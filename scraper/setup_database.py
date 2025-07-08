#!/usr/bin/env python3
"""
Database setup script for Stanford Research Opportunities scraper.
This script creates all necessary database tables.
"""

import sys
import os
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import text

# Add backend to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

try:
    from app.database import init_database, test_connection, engine
    from app.models import Base
    logger.info("✅ Successfully imported database modules")
except ImportError as e:
    logger.error(f"❌ Failed to import database modules: {e}")
    sys.exit(1)


def main():
    """Initialize database with all required tables."""
    logger.info("🚀 Starting database initialization...")
    
    # Test connection first
    logger.info("🔌 Testing database connection...")
    if not test_connection():
        logger.error("❌ Database connection failed!")
        sys.exit(1)
    
    logger.info("✅ Database connection successful")
    
    # Initialize database
    try:
        logger.info("📊 Creating database tables...")
        init_database()
        logger.info("✅ Database initialization completed successfully!")
        
        # Verify tables were created
        logger.info("🔍 Verifying table creation...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM opportunities"))
            logger.info(f"✅ Opportunities table ready (current count: {result.scalar()})")
            
        logger.info("🎉 Database setup complete! Ready for scraping.")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 