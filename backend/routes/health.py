"""
Health check routes for Flask application
Converted from FastAPI health endpoints
"""

from flask import Blueprint, jsonify
from datetime import datetime
import os

health_bp = Blueprint('health', __name__)

@health_bp.route('/ping')
def ping():
    """Simple ping endpoint for testing connectivity."""
    return jsonify({"message": "pong", "status": "ok"})

@health_bp.route('/health')
def health_check():
    """Health check endpoint for monitoring and deployment."""
    try:
        return jsonify({
            "status": "ok",
            "message": "Stanford Research Opportunities API is healthy",
            "version": "1.0.0-flask",
            "timestamp": datetime.now().isoformat(),
            "environment": os.getenv("STAGE", "prod"),
            "database_configured": bool(os.getenv("DATABASE_URL")),
            "framework": "Flask"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Health check failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500

@health_bp.route('/healthz')
def healthz():
    """Alternative health check endpoint (Kubernetes style)."""
    return jsonify({"status": "ok"})

@health_bp.route('/ready')
def ready():
    """Readiness check endpoint."""
    return jsonify({
        "status": "ready",
        "timestamp": datetime.now().isoformat()
    }) 