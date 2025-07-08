#!/usr/bin/env python3
"""
Test script for API authentication
Tests both local and deployed endpoints with and without auth
"""

import requests
import sys
import json
import os
from datetime import datetime

def test_endpoint_auth(base_url, endpoint, api_key=None, expected_status=200):
    """Test an API endpoint with authentication."""
    url = f"{base_url}{endpoint}"
    headers = {}
    auth_desc = "with auth" if api_key else "without auth"
    
    if api_key:
        headers['X-API-Key'] = api_key
    
    # Also test with origin header
    headers['Origin'] = 'https://samihsq.github.io'
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        status_desc = "✅" if response.status_code == expected_status else "❌"
        print(f"{status_desc} GET {endpoint} ({auth_desc}) - Status: {response.status_code}")
        
        if response.status_code != expected_status:
            print(f"   Expected {expected_status}, got {response.status_code}")
            if response.status_code in [401, 403]:
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data.get('message', 'Unknown error')}")
                except:
                    print(f"   Response: {response.text[:200]}")
        
        return response.status_code == expected_status, response
        
    except requests.exceptions.RequestException as e:
        print(f"❌ GET {endpoint} ({auth_desc}) - Error: {e}")
        return False, None

def test_auth_system(base_url, api_key):
    """Test the authentication system comprehensively."""
    
    print(f"🔐 Testing Authentication at: {base_url}")
    print(f"🔑 Using API Key: {api_key[:10]}..." if api_key else "🔑 No API Key provided")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test endpoints that should NOT require auth (health checks)
    public_endpoints = [
        ('/health', 200),
        ('/ping', 200),
        ('/healthz', 200),
        ('/ready', 200),
        ('/', 200),
    ]
    
    print("📋 Testing Public Endpoints (should work without auth):")
    for endpoint, expected_status in public_endpoints:
        tests_total += 1
        success, response = test_endpoint_auth(base_url, endpoint, None, expected_status)
        if success:
            tests_passed += 1
    
    print("\n🔒 Testing Protected Endpoints without auth (should fail):")
    protected_endpoints = [
        ('/api/opportunities', 401),
        ('/api/opportunities/count', 401),
        ('/api/opportunities/stats', 401),
        ('/api/opportunities/departments/list', 401),
    ]
    
    for endpoint, expected_status in protected_endpoints:
        tests_total += 1
        success, response = test_endpoint_auth(base_url, endpoint, None, expected_status)
        if success:
            tests_passed += 1
    
    if api_key:
        print(f"\n🔓 Testing Protected Endpoints with auth (should work):")
        for endpoint, _ in protected_endpoints:
            tests_total += 1
            success, response = test_endpoint_auth(base_url, endpoint, api_key, 200)
            if success:
                tests_passed += 1
                
                # Show some data for successful requests
                if response and endpoint == '/api/opportunities/count':
                    try:
                        data = response.json()
                        print(f"   Total opportunities: {data.get('total', 0)}")
                    except:
                        pass
    
    # Test auth info endpoint
    print(f"\n🔍 Testing Auth Info Endpoint:")
    tests_total += 1
    success, response = test_endpoint_auth(base_url, '/auth/info', api_key, 200)
    if success and response:
        tests_passed += 1
        try:
            auth_info = response.json()
            print(f"   Authenticated: {auth_info.get('authenticated', False)}")
            print(f"   Allowed Origins: {len(auth_info.get('allowed_origins', []))} origins")
            print(f"   API Key Configured: {auth_info.get('has_api_key_configured', False)}")
        except:
            pass
    
    print("\n" + "=" * 60)
    print(f"📊 Authentication Test Results: {tests_passed}/{tests_total} tests passed")
    
    if tests_passed == tests_total:
        print("🎉 All authentication tests passed! Your API security is working correctly.")
        return True
    else:
        print("⚠️  Some authentication tests failed. Check the output above for details.")
        return False

def test_wrong_api_key(base_url):
    """Test with wrong API key to ensure it's rejected."""
    print(f"\n🚫 Testing with Wrong API Key:")
    wrong_key = "wrong-api-key-should-fail"
    success, response = test_endpoint_auth(base_url, '/api/opportunities/count', wrong_key, 401)
    return success

def main():
    """Main function to run authentication tests."""
    
    if len(sys.argv) > 1:
        # Use provided URL
        base_url = sys.argv[1].rstrip('/')
    else:
        # Default to local development
        base_url = "http://localhost:8000"
    
    # Get API key from environment or command line
    api_key = os.getenv("API_KEY")
    if len(sys.argv) > 2:
        api_key = sys.argv[2]
    
    if not api_key:
        api_key = "dev-api-key-change-in-production"  # Default for testing
    
    print(f"🔐 Stanford Research Opportunities API - Authentication Test Suite")
    print(f"🕐 Test started at: {datetime.now().isoformat()}")
    print()
    
    success = test_auth_system(base_url, api_key)
    
    # Test wrong API key
    wrong_key_success = test_wrong_api_key(base_url)
    
    if success and wrong_key_success:
        print("\n✅ All authentication tests passed!")
        print("\n💡 Usage:")
        print("  - Local testing: python test_auth.py")
        print("  - Local with API key: python test_auth.py http://localhost:8000 your-api-key")
        print("  - Deployed API: python test_auth.py https://your-api-url your-api-key")
        print("  - With env var: API_KEY=your-key python test_auth.py https://your-api-url")
        sys.exit(0)
    else:
        print("\n❌ Authentication tests failed. Please check the configuration.")
        print("\n🔧 Troubleshooting:")
        print("  - Ensure API_KEY environment variable is set in the backend")
        print("  - Check that the frontend is using the same API key")
        print("  - Verify CORS origins are configured correctly")
        print("  - Check CloudWatch logs for detailed error messages")
        sys.exit(1)

if __name__ == "__main__":
    main() 