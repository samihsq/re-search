"""
Flask application for Stanford Research Opportunities API
Converted from FastAPI for better Lambda compatibility
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from werkzeug.exceptions import HTTPException

# Import configurations and models
from config import get_settings
from models import db, Opportunity, UserPreference, NotificationSent, ScrapingLog
from routes.opportunities import opportunities_bp
from routes.health import health_bp
from auth import get_auth_info, require_auth_optional

def create_app():
    """Application factory pattern for Flask app creation."""
    
    app = Flask(__name__)
    
    # Load configuration
    settings = get_settings()
    app.config['SQLALCHEMY_DATABASE_URI'] = settings.database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = settings.secret_key or 'dev-secret-key'
    
    # Disable strict slashes globally to prevent 308 redirects.
    # This makes routes like /opportunities and /opportunities/ behave the same.
    app.url_map.strict_slashes = False
    
    # Initialize extensions
    db.init_app(app)
    
    # Configure CORS
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:8000", 
        "https://localhost:3000",
        "https://localhost:8000",
        "https://samihsq.github.io",  # GitHub Pages domain
        "https://samihsq.github.io/re-search",  # GitHub Pages with repo path
    ]
    
    # Add production origins
    if not settings.debug:
        production_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
        allowed_origins.extend([origin.strip() for origin in production_origins if origin.strip()])
    
    CORS(app, origins=allowed_origins, supports_credentials=True)
    
    # Register blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(opportunities_bp, url_prefix='/api/opportunities')
    
    # Authentication info endpoint
    @app.route('/auth/info')
    @require_auth_optional
    def auth_info():
        """Get authentication configuration info (for debugging)."""
        info = get_auth_info()
        info['endpoint'] = 'main.auth_info'
        info['authenticated'] = bool(request.headers.get('X-API-Key'))
        info['headers_received'] = dict(request.headers)
        return jsonify(info)
    
    # Create database tables (only if DATABASE_URL is properly configured)
    database_url = settings.database_url
    if database_url and database_url != "postgresql://postgres:password@localhost:5432/stanford_opportunities":
        with app.app_context():
            try:
                db.create_all()
                print("✅ Database tables created successfully")
            except Exception as e:
                print(f"⚠️  Database tables creation failed: {e}")
                print("📝 App will continue running. Check DATABASE_URL configuration.")
    else:
        print("📝 No database URL configured, skipping database initialization")
    
    # Error handlers
    @app.errorhandler(HTTPException)
    def handle_exception(e):
        """Return JSON instead of HTML for HTTP errors."""
        return jsonify({
            "error": e.name,
            "message": e.description,
            "status_code": e.code
        }), e.code
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "error": "Not found",
            "message": "The requested resource was not found",
            "status_code": 404
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "status_code": 500
        }), 500
    
    # Root endpoint
    @app.route('/')
    def root():
        """Root endpoint with API information."""
        return jsonify({
            "message": "Stanford Research Opportunities API",
            "version": "1.0.0-flask",
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "docs": "/docs",
            "health": "/health",
            "endpoints": {
                "opportunities": "/api/opportunities",
                "health": "/health",
                "ping": "/ping"
            }
        })
    
    return app

# Create the application instance
app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000) 