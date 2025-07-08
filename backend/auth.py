"""
Authentication middleware for Flask API
Provides API key authentication and origin validation
"""

from functools import wraps
from flask import request, jsonify, current_app
import os
import hashlib
import hmac
from typing import Optional, List

class AuthConfig:
    """Authentication configuration."""
    
    def __init__(self):
        # API key for frontend authentication
        self.api_key = os.getenv("API_KEY", "dev-api-key-change-in-production")
        self.api_key_header = "X-API-Key"
        
        # Allowed origins (same as CORS origins)
        allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "")
        self.allowed_origins = [
            "http://localhost:3000",
            "http://localhost:8000", 
            "https://localhost:3000",
            "https://localhost:8000",
            "https://samihsq.github.io",  # GitHub Pages
        ]
        
        # Add production origins from environment
        if allowed_origins_str:
            production_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]
            self.allowed_origins.extend(production_origins)
        
        # Optional: Referrer validation
        self.check_referrer = os.getenv("CHECK_REFERRER", "true").lower() == "true"
        
        # Rate limiting settings
        self.rate_limit_enabled = os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true"
        self.rate_limit_requests = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
        self.rate_limit_window = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds

auth_config = AuthConfig()

def validate_api_key(provided_key: str) -> bool:
    """Validate the provided API key."""
    expected_key = auth_config.api_key
    
    # Use constant-time comparison to prevent timing attacks
    if len(provided_key) != len(expected_key):
        return False
    
    return hmac.compare_digest(provided_key.encode(), expected_key.encode())

def validate_origin(origin: Optional[str]) -> bool:
    """Validate the request origin."""
    if not origin:
        # Allow requests without origin header (e.g., Postman, curl)
        # But only if we're in development mode
        return current_app.config.get('DEBUG', False)
    
    # Check if origin is in allowed list
    return origin in auth_config.allowed_origins

def validate_referrer(referrer: Optional[str]) -> bool:
    """Validate the request referrer."""
    if not auth_config.check_referrer:
        return True
    
    if not referrer:
        return not auth_config.check_referrer  # Allow if referrer checking is disabled
    
    # Check if referrer starts with allowed origins
    for allowed_origin in auth_config.allowed_origins:
        if referrer.startswith(allowed_origin):
            return True
    
    return False

def require_auth(f):
    """
    Decorator to require authentication for API endpoints.
    Validates API key, origin, and optionally referrer.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get request headers
        api_key = request.headers.get(auth_config.api_key_header)
        origin = request.headers.get('Origin')
        referrer = request.headers.get('Referer')
        
        # Skip auth for OPTIONS requests (CORS preflight)
        if request.method == 'OPTIONS':
            return f(*args, **kwargs)
        
        # Validate API key
        if not api_key:
            return jsonify({
                'error': 'Authentication required',
                'message': f'Missing {auth_config.api_key_header} header'
            }), 401
        
        if not validate_api_key(api_key):
            current_app.logger.warning(f"Invalid API key attempt from {request.remote_addr}")
            return jsonify({
                'error': 'Invalid API key',
                'message': 'The provided API key is invalid'
            }), 401
        
        # Validate origin
        if not validate_origin(origin):
            current_app.logger.warning(f"Request from unauthorized origin: {origin}")
            return jsonify({
                'error': 'Unauthorized origin',
                'message': 'Requests from this origin are not allowed'
            }), 403
        
        # Validate referrer (optional)
        if not validate_referrer(referrer):
            current_app.logger.warning(f"Request from unauthorized referrer: {referrer}")
            return jsonify({
                'error': 'Unauthorized referrer',
                'message': 'Requests from this referrer are not allowed'
            }), 403
        
        # Log successful authentication (for monitoring)
        current_app.logger.info(f"Authenticated request from {origin} to {request.endpoint}")
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_auth_optional(f):
    """
    Decorator for optional authentication.
    Validates auth if provided, but allows requests without auth.
    Useful for endpoints that have both public and authenticated access.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get(auth_config.api_key_header)
        
        # If API key is provided, validate it
        if api_key:
            if not validate_api_key(api_key):
                return jsonify({
                    'error': 'Invalid API key',
                    'message': 'The provided API key is invalid'
                }), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

def get_auth_info():
    """Get authentication configuration info (for debugging)."""
    return {
        'api_key_header': auth_config.api_key_header,
        'allowed_origins': auth_config.allowed_origins,
        'check_referrer': auth_config.check_referrer,
        'rate_limit_enabled': auth_config.rate_limit_enabled,
        'has_api_key_configured': bool(auth_config.api_key and auth_config.api_key != "dev-api-key-change-in-production")
    } 