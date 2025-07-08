#!/usr/bin/env python3
"""
Test script for Flask API deployment with AWS SAM
Tests both local and deployed endpoints
"""

import requests
import sys
import json
from datetime import datetime

def test_endpoint(base_url, endpoint, method='GET', data=None, expected_status=200):
    """Test an API endpoint."""
    url = f"{base_url}{endpoint}"
    
    try:
        if method == 'GET':
            response = requests.get(url, timeout=10)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=10)
        elif method == 'PUT':
            response = requests.put(url, json=data, timeout=10)
        elif method == 'DELETE':
            response = requests.delete(url, timeout=10)
        
        print(f"✅ {method} {endpoint} - Status: {response.status_code}")
        
        if response.status_code == expected_status:
            return True, response.json()
        else:
            print(f"❌ Expected {expected_status}, got {response.status_code}")
            return False, None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ {method} {endpoint} - Error: {e}")
        return False, None

def test_api(base_url):
    """Test the Flask API endpoints."""
    
    print(f"🧪 Testing API at: {base_url}")
    print("=" * 50)
    
    tests_passed = 0
    tests_total = 0
    
    # Test health endpoints
    endpoints_to_test = [
        ('/health', 'GET', 200),
        ('/ping', 'GET', 200),
        ('/healthz', 'GET', 200),
        ('/ready', 'GET', 200),
        ('/', 'GET', 200),
        ('/api/opportunities', 'GET', 200),
        ('/api/opportunities/count', 'GET', 200),
        ('/api/opportunities/stats', 'GET', 200),
        ('/api/opportunities/departments/list', 'GET', 200),
        ('/api/opportunities/recent', 'GET', 200),
    ]
    
    for endpoint, method, expected_status in endpoints_to_test:
        tests_total += 1
        success, response_data = test_endpoint(base_url, endpoint, method, expected_status=expected_status)
        if success:
            tests_passed += 1
            
            # Print some key info for important endpoints
            if endpoint == '/health' and response_data:
                print(f"   Framework: {response_data.get('framework', 'Unknown')}")
                print(f"   Version: {response_data.get('version', 'Unknown')}")
                print(f"   Environment: {response_data.get('environment', 'Unknown')}")
            
            elif endpoint == '/api/opportunities/count' and response_data:
                print(f"   Total opportunities: {response_data.get('total', 0)}")
                
            elif endpoint == '/api/opportunities/stats' and response_data:
                print(f"   Active opportunities: {response_data.get('active_opportunities', 0)}")
                print(f"   Departments: {response_data.get('departments', 0)}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tests_passed}/{tests_total} tests passed")
    
    if tests_passed == tests_total:
        print("🎉 All tests passed! Your API is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False

def main():
    """Main function to run tests."""
    
    if len(sys.argv) > 1:
        # Use provided URL
        base_url = sys.argv[1].rstrip('/')
    else:
        # Default to local development
        base_url = "http://localhost:8000"
    
    print(f"🚀 Stanford Research Opportunities API - Flask + AWS SAM Test Suite")
    print(f"🕐 Test started at: {datetime.now().isoformat()}")
    print()
    
    success = test_api(base_url)
    
    if success:
        print("\n✅ API is healthy and ready for use!")
        print("\n💡 Tips:")
        print("  - For local testing: python test_api.py")
        print("  - For deployed API: python test_api.py https://your-api-url")
        print("  - View SAM logs: sam logs -n FlaskApiFunction --stack-name stanford-research-api-dev --tail")
        sys.exit(0)
    else:
        print("\n❌ API tests failed. Please check the configuration.")
        print("\n🔧 Troubleshooting:")
        print("  - Check if Flask app is running locally")
        print("  - Verify AWS SAM deployment completed successfully")
        print("  - Check CloudWatch logs for errors")
        sys.exit(1)

if __name__ == "__main__":
    main() 