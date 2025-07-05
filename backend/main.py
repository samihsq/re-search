from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
from datetime import datetime

from app.api import opportunities
from app.database import engine, Base
from app.config import settings

# Add static file serving imports
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")
except Exception as e:
    print(f"⚠️  Database tables creation failed: {e}")
    print("📝 App will continue running. Add DATABASE_URL to fix database connection.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Stanford Research Opportunities API...")
    yield
    # Shutdown
    print("🛑 Shutting down Stanford Research Opportunities API...")

app = FastAPI(
    title="Stanford Research Opportunities API",
    description="API for aggregating and searching Stanford research opportunities",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
allowed_origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "https://localhost:3000",
    "https://localhost:8000",
]

# Add production origins from environment
if settings.debug is False:
    # Add Railway and production origins
    production_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
    allowed_origins.extend([origin.strip() for origin in production_origins if origin.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(opportunities.router, prefix="/api/opportunities", tags=["opportunities"])

# Health check endpoints - MUST come before catch-all route
@app.get("/ping")
async def ping():
    """Simple ping endpoint for testing connectivity."""
    return {"message": "pong", "timestamp": datetime.now().isoformat()}

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and Railway deployment."""
    # Simple health check that always returns 200 for Railway
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "message": "API is running"
    }

@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with database and Redis status."""
    # Always return 200 for Railway health checks, but include component status
    db_status = "not_configured"
    try:
        # Test database connection
        from app.database import SessionLocal
        if SessionLocal:
            db = SessionLocal()
            db.execute("SELECT 1")
            db.close()
            db_status = "healthy"
        else:
            db_status = "not_configured - add DATABASE_URL environment variable"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Test Redis connection (if available)
    redis_status = "not_configured"
    try:
        import redis
        r = redis.from_url(settings.redis_url)
        r.ping()
        redis_status = "healthy"
    except Exception as e:
        redis_status = f"unhealthy: {str(e)}"
    
    health_data = {
        "status": "healthy",  # Always healthy for Railway
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "database": db_status,
        "redis": redis_status,
        "environment": "production" if not settings.debug else "development",
        "llm_parsing": "enabled" if settings.enable_llm_parsing else "disabled",
        "message": "API is running. Database and Redis status shown separately."
    }
    
    # Always return 200 for Railway health checks
    return JSONResponse(content=health_data, status_code=200)

@app.get("/api/health")
async def api_health():
    """Alternative health check endpoint."""
    return await health_check()

# Mount static files (React frontend)
if os.path.exists("/app/static"):
    app.mount("/static", StaticFiles(directory="/app/static"), name="static")
    
    # Serve React app at root
    @app.get("/")
    async def serve_frontend():
        """Serve the React frontend."""
        return FileResponse("/app/static/index.html")
    
    # Catch-all route for React Router - MUST come last
    @app.get("/{path:path}")
    async def serve_frontend_routes(path: str):
        """Serve React frontend for all unmatched routes (SPA routing)."""
        # Don't serve static files or API routes through this
        if path.startswith(("api/", "docs", "redoc", "openapi.json", "health", "ping")):
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse("/app/static/index.html")
else:
    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "message": "Stanford Research Opportunities API",
            "version": "1.0.0",
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "docs": "/docs",
            "health": "/health",
            "ping": "/ping"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    ) 