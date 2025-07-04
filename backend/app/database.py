from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import os
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/stanford_opportunities"
)

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=os.getenv("DB_ECHO", "false").lower() == "true"
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()

# Global flag to track if pgvector is available
PGVECTOR_AVAILABLE = False


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables in the database."""
    from .models import Base
    Base.metadata.create_all(bind=engine)


def setup_pgvector():
    """Setup pgvector extension for vector similarity search (optional)."""
    global PGVECTOR_AVAILABLE
    try:
        with engine.connect() as connection:
            # Enable pgvector extension
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            connection.commit()
            PGVECTOR_AVAILABLE = True
            logger.info("pgvector extension enabled successfully")
            return True
    except Exception as e:
        logger.warning(f"pgvector extension not available (this is optional): {e}")
        PGVECTOR_AVAILABLE = False
        return False


def create_vector_table():
    """Create table for storing opportunity embeddings (optional)."""
    if not PGVECTOR_AVAILABLE:
        logger.info("Skipping vector table creation - pgvector not available")
        return False
        
    create_vector_sql = """
    CREATE TABLE IF NOT EXISTS opportunity_embeddings (
        id SERIAL PRIMARY KEY,
        opportunity_id INTEGER REFERENCES opportunities(id) ON DELETE CASCADE,
        embedding vector(1536),  -- OpenAI embedding dimension
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(opportunity_id)
    );
    
    CREATE INDEX IF NOT EXISTS opportunity_embeddings_embedding_idx 
    ON opportunity_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
    """
    
    try:
        with engine.connect() as connection:
            connection.execute(text(create_vector_sql))
            connection.commit()
            logger.info("Vector table created successfully")
            return True
    except Exception as e:
        logger.warning(f"Failed to create vector table (this is optional): {e}")
        return False


def init_database():
    """Initialize database with all required tables and extensions."""
    logger.info("Initializing database...")
    
    try:
        # Create all tables (required)
        create_tables()
        logger.info("Database tables created")
        
        # Setup vector extension and table (optional)
        pgvector_success = setup_pgvector()
        if pgvector_success:
            create_vector_table()
            logger.info("Vector search capabilities enabled")
        else:
            logger.info("Vector search capabilities disabled (pgvector not available)")
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def test_connection():
    """Test database connection."""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
            return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


def is_pgvector_available():
    """Check if pgvector is available for use."""
    return PGVECTOR_AVAILABLE


# Health check queries
HEALTH_CHECK_QUERIES = {
    "opportunities_count": "SELECT COUNT(*) FROM opportunities WHERE is_active = true",
    "recent_scraping": """
        SELECT COUNT(*) FROM scraping_logs 
        WHERE scraping_started_at > NOW() - INTERVAL '24 hours'
    """,
    "active_users": "SELECT COUNT(*) FROM user_preferences WHERE is_active = true"
} 