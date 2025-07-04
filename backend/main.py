from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import sys
import os
from contextlib import asynccontextmanager
from datetime import datetime

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.config import settings
from app.database import init_database, test_connection
from app.api.opportunities import router as opportunities_router
from loguru import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Test database connection
    if not test_connection():
        logger.error("Database connection failed")
        raise Exception("Database connection failed")
    
    # Initialize database
    try:
        init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    logger.info("Application startup completed")
    yield
    
    # Shutdown
    logger.info("Shutting down application...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    Stanford Research Opportunities Aggregator API
    
    This API provides access to research funding, internship, and research opportunities
    aggregated from multiple Stanford websites. Features include:
    
    - Comprehensive opportunity database
    - Intelligent semantic search powered by LLM
    - Real-time notifications and subscriptions
    - Advanced filtering and analytics
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Add trusted host middleware for security
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.stanford.edu"]
)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    from app.database import engine, HEALTH_CHECK_QUERIES
    from sqlalchemy import text
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.app_version,
        "database": "connected",
        "checks": {}
    }
    
    # Test database connection and run health checks
    try:
        with engine.connect() as connection:
            for check_name, query in HEALTH_CHECK_QUERIES.items():
                try:
                    result = connection.execute(text(query))
                    count = result.scalar()
                    health_status["checks"][check_name] = count
                except Exception as e:
                    health_status["checks"][check_name] = f"error: {str(e)}"
                    health_status["status"] = "degraded"
    
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["database"] = f"error: {str(e)}"
        return JSONResponse(
            status_code=503,
            content=health_status
        )
    
    return health_status


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    logger.error(f"HTTP error {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "detail": str(exc) if settings.debug else "An unexpected error occurred"
        }
    )


# Include API routers
app.include_router(opportunities_router, prefix="/api/opportunities", tags=["opportunities"])

# Additional routers to be added:
# from app.api.search import router as search_router  
# from app.api.notifications import router as notifications_router
# from app.api.admin import router as admin_router

# app.include_router(search_router, prefix="/api/search", tags=["search"])
# app.include_router(notifications_router, prefix="/api/notifications", tags=["notifications"])
# app.include_router(admin_router, prefix="/api/admin", tags=["admin"])


if __name__ == "__main__":
    # Configure logging
    logger.remove()  # Remove default handler
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    if settings.log_file:
        logger.add(
            settings.log_file,
            level=settings.log_level,
            rotation="1 day",
            retention="30 days",
            compression="gz"
        )
    
    # Run the application
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_config=None  # Use loguru instead of uvicorn's logging
    ) 