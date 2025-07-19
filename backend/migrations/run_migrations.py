"""Script to run database migrations."""

import os
import sys
from sqlalchemy import create_engine, text
from loguru import logger

# Add parent directory to path so we can import from backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_settings

def run_migrations():
    """Run all migration files in order."""
    settings = get_settings()
    
    # Create database engine
    engine = create_engine(settings.database_url)
    
    try:
        # Get the migration file
        migration_file = os.path.join(
            os.path.dirname(__file__),
            'add_full_text_search.sql'
        )
        
        # Read and execute the migration
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
            
        with engine.connect() as conn:
            # Execute migration in a transaction
            with conn.begin():
                logger.info(f"Running migration: {migration_file}")
                conn.execute(text(migration_sql))
                logger.success(f"Successfully ran migration: {migration_file}")
        
        logger.success("All migrations completed successfully!")
        
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        sys.exit(1)

if __name__ == '__main__':
    run_migrations() 