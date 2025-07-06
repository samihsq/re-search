"""
AWS Lambda handler for Stanford Research Opportunities API
Serves the FastAPI application in a serverless environment
"""

import sys
import os
import json
from typing import Dict, Any

# Add current directory to Python path
sys.path.insert(0, '/var/task')
sys.path.insert(0, '/var/task/backend')
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function handler for API Gateway events.
    Routes requests to the FastAPI application.
    """
    
    # Basic health check response
    if event.get('rawPath') == '/health' or event.get('path') == '/health':
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            },
            "body": json.dumps({
                "status": "ok",
                "message": "Stanford Research Opportunities API is running",
                "version": "1.0.0",
                "environment": os.getenv("STAGE", "prod")
            })
        }
    
    try:
        # Try to import and use FastAPI app
        from mangum import Mangum
        
        # Try different import paths
        app = None
        try:
            from main import app
        except ImportError:
            try:
                from backend.main import app
            except ImportError:
                # Create a minimal FastAPI app as fallback
                from fastapi import FastAPI
                from fastapi.middleware.cors import CORSMiddleware
                
                app = FastAPI(title="Stanford Research Opportunities API")
                
                app.add_middleware(
                    CORSMiddleware,
                    allow_origins=["*"],
                    allow_credentials=True,
                    allow_methods=["*"],
                    allow_headers=["*"],
                )
                
                @app.get("/health")
                def health_check():
                    return {"status": "ok", "message": "API is running"}
                
                @app.get("/api/opportunities")
                def get_opportunities():
                    return {"opportunities": [], "message": "Database connection needed"}
        
        # Create Mangum adapter for AWS Lambda
        asgi_handler = Mangum(app, lifespan="off")
        
        # Handle the request
        return asgi_handler(event, context)
        
    except Exception as e:
        print(f"Lambda handler error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            },
            "body": json.dumps({
                "error": "Internal server error",
                "message": str(e),
                "path": event.get("rawPath", "unknown")
            })
        }
