"""
Lambda handler for AWS SAM deployment
Wraps the Flask application for AWS Lambda
"""

import json
import base64
from app import app

def handler(event, context):
    """
    Lambda handler function that wraps the Flask app for AWS API Gateway.
    Compatible with AWS SAM deployment.
    """
    
    # Handle API Gateway proxy integration
    if 'httpMethod' in event:
        # API Gateway proxy integration format
        return handle_api_gateway_proxy(event, context)
    else:
        # Direct invocation or other event types
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Stanford Research Opportunities API',
                'version': '1.0.0-flask-sam',
                'event_type': 'direct_invocation'
            })
        }

def handle_api_gateway_proxy(event, context):
    """Handle API Gateway proxy integration events."""
    
    # Extract request details from the event
    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '/')
    query_string_parameters = event.get('queryStringParameters') or {}
    headers = event.get('headers') or {}
    body = event.get('body', '')
    is_base64_encoded = event.get('isBase64Encoded', False)
    
    # Decode body if base64 encoded
    if is_base64_encoded and body:
        body = base64.b64decode(body).decode('utf-8')
    
    # Create a test client for the Flask app
    with app.test_client() as client:
        # Build query string
        query_string = ''
        if query_string_parameters:
            query_params = []
            for key, value in query_string_parameters.items():
                if value is not None:
                    query_params.append(f"{key}={value}")
            if query_params:
                query_string = '?' + '&'.join(query_params)
        
        # Make the request to Flask
        full_path = path + query_string
        
        # Set up headers for the request
        flask_headers = {}
        for key, value in headers.items():
            # Convert API Gateway headers to Flask format
            if key.lower() not in ['host', 'content-length']:
                flask_headers[key] = value
        
        try:
            # Make the request
            if http_method == 'GET':
                response = client.get(full_path, headers=flask_headers)
            elif http_method == 'POST':
                response = client.post(full_path, data=body, headers=flask_headers, 
                                     content_type=headers.get('Content-Type', 'application/json'))
            elif http_method == 'PUT':
                response = client.put(full_path, data=body, headers=flask_headers,
                                    content_type=headers.get('Content-Type', 'application/json'))
            elif http_method == 'DELETE':
                response = client.delete(full_path, headers=flask_headers)
            elif http_method == 'OPTIONS':
                response = client.options(full_path, headers=flask_headers)
            else:
                # Unsupported method
                return {
                    'statusCode': 405,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Key'
                    },
                    'body': json.dumps({
                        'error': 'Method not allowed',
                        'message': f'HTTP method {http_method} is not supported'
                    })
                }
            
            # Convert Flask response to API Gateway format
            response_headers = {}
            for key, value in response.headers:
                response_headers[key] = value
            
            # Ensure CORS headers are present
            response_headers['Access-Control-Allow-Origin'] = '*'
            response_headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response_headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token, X-Amz-User-Agent, X-API-Key'
            
            # Get response body
            response_body = response.get_data(as_text=True)
            
            return {
                'statusCode': response.status_code,
                'headers': response_headers,
                'body': response_body,
                'isBase64Encoded': False
            }
            
        except Exception as e:
            # Handle errors
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Key'
                },
                'body': json.dumps({
                    'error': 'Internal server error',
                    'message': str(e)
                })
            } 