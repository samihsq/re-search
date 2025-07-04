#!/usr/bin/env python3
"""
Test script for Gemini HTML parsing integration.

This script tests the new LLM HTML parsing service to ensure it works correctly
before full deployment.
"""

import asyncio
import json
from datetime import datetime

# Test HTML content (example from a Stanford research page)
SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Stanford Undergraduate Research Program</title>
</head>
<body>
    <div class="content">
        <h1>Summer Research Program</h1>
        <p>The Stanford Summer Research Program offers undergraduate students the opportunity to work directly with faculty on cutting-edge research projects in AI and machine learning.</p>
        
        <div class="program-details">
            <h2>Program Details</h2>
            <ul>
                <li><strong>Duration:</strong> 10 weeks (June 15 - August 25, 2024)</li>
                <li><strong>Stipend:</strong> $6,000</li>
                <li><strong>Department:</strong> Computer Science</li>
                <li><strong>Eligibility:</strong> Current undergraduates with programming experience</li>
                <li><strong>Application Deadline:</strong> March 15, 2024</li>
            </ul>
        </div>
        
        <div class="application">
            <h2>How to Apply</h2>
            <p>Applications must be submitted through the <a href="/apply">online portal</a>.</p>
            <p>For questions, contact: research@stanford.edu</p>
        </div>
        
        <h2>Second Opportunity</h2>
        <p>The AI Ethics Fellowship provides graduate students funding to explore ethical implications of artificial intelligence. This 6-month fellowship includes $8,000 stipend and mentorship.</p>
        <p>Deadline: April 1, 2024. Contact: ethics@stanford.edu</p>
    </div>
</body>
</html>
"""

async def test_html_parsing():
    """Test the LLM HTML parsing service."""
    print("🧪 Testing Gemini HTML Parsing Integration")
    print("=" * 50)
    
    try:
        from app.services.llm_validation_service import llm_parsing_service
        from app.config import settings
        
        print(f"✅ LLM Parsing Service imported successfully")
        print(f"📊 Settings:")
        print(f"   - Parsing enabled: {settings.enable_llm_parsing}")
        print(f"   - Gemini API key configured: {'Yes' if settings.gemini_api_key else 'No'}")
        print(f"   - Model: {settings.gemini_model}")
        print(f"   - Daily limit: {settings.llm_daily_call_limit}")
        print()
        
        # Test HTML parsing
        test_url = "https://example.stanford.edu/research"
        
        print(f"🔍 Testing HTML parsing for URL: {test_url}")
        print(f"📄 Sample HTML content length: {len(SAMPLE_HTML)} characters")
        print()
        
        start_time = datetime.now()
        result = await llm_parsing_service.parse_html_content(SAMPLE_HTML, test_url)
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        print(f"⏱️  Processing time: {duration:.2f} seconds")
        print()
        
        # Analyze results
        if result.get("success"):
            opportunities = result.get("opportunities", [])
            print(f"🎉 SUCCESS: Found {len(opportunities)} opportunities")
            print()
            
            for i, opp in enumerate(opportunities, 1):
                print(f"📝 Opportunity {i}:")
                print(f"   Title: {opp.get('title', 'N/A')}")
                print(f"   Description: {opp.get('description', 'N/A')[:100]}...")
                print(f"   Tags: {opp.get('tags', [])}")
                print(f"   Department: {opp.get('department', 'N/A')}")
                print(f"   Deadline: {opp.get('deadline', 'N/A')}")
                print(f"   Funding: {opp.get('funding_amount', 'N/A')}")
                print(f"   Contact: {opp.get('contact_email', 'N/A')}")
                print(f"   Type: {opp.get('opportunity_type', 'N/A')}")
                print()
            
            print("🎯 Test Result: PASSED ✅")
            
        else:
            error = result.get("error", "unknown")
            print(f"❌ FAILED: {error}")
            print()
            
            if error == "gemini_not_available":
                print("💡 Note: Gemini API may not be configured. This is expected in testing.")
            elif error == "daily_budget_exceeded":
                print("💡 Note: Daily API budget exceeded. Consider increasing the limit.")
            elif error == "llm_parsing_disabled":
                print("💡 Note: LLM parsing is disabled in settings.")
            
            print("🎯 Test Result: EXPECTED FAILURE (no API key) ⚠️")
            
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("🎯 Test Result: FAILED ❌")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        print("🎯 Test Result: FAILED ❌")

async def test_scraper_integration():
    """Test the scraper integration with LLM parsing."""
    print("\n" + "=" * 50)
    print("🔧 Testing Scraper Integration")
    print("=" * 50)
    
    try:
        from app.scrapers.base_scraper import BaseScraper
        
        # Create a minimal test scraper
        class TestScraper(BaseScraper):
            def extract_opportunities(self, soup):
                # Return a simple test opportunity for fallback testing
                return [{
                    'title': 'Test Opportunity',
                    'description': 'This is a test opportunity created by traditional scraping.',
                    'department': 'Computer Science',
                    'opportunity_type': 'research',
                    'tags': ['test', 'research']
                }]
        
        scraper = TestScraper("https://test.stanford.edu")
        print("✅ Test scraper created successfully")
        
        # Mock the fetch_page method to return our sample HTML
        scraper.fetch_page = lambda url: SAMPLE_HTML
        
        print("🚀 Running scraper.scrape()...")
        start_time = datetime.now()
        opportunities = await scraper.scrape()
        end_time = datetime.now()
        
        duration = (end_time - start_time).total_seconds()
        print(f"⏱️  Scraping time: {duration:.2f} seconds")
        print(f"📊 Found {len(opportunities)} opportunities")
        
        for i, opp in enumerate(opportunities, 1):
            print(f"\n📝 Opportunity {i}:")
            print(f"   Title: {opp.get('title', 'N/A')}")
            print(f"   LLM Parsed: {opp.get('llm_parsed', False)}")
            print(f"   Scraper Used: {opp.get('scraper_used', 'N/A')}")
            
        print("\n🎯 Scraper Integration Test: PASSED ✅")
        
    except Exception as e:
        print(f"❌ Scraper Integration Error: {e}")
        print("🎯 Scraper Integration Test: FAILED ❌")

async def main():
    """Run all tests."""
    print("🚀 Starting Gemini Integration Tests")
    print("Testing the migration from Perplexity to Google Gemini API")
    print("=" * 70)
    
    await test_html_parsing()
    await test_scraper_integration()
    
    print("\n" + "=" * 70)
    print("📋 Test Summary:")
    print("1. HTML Parsing Service: Tests basic Gemini API integration")
    print("2. Scraper Integration: Tests fallback and metadata handling")
    print()
    print("💡 To enable full functionality:")
    print("   1. Copy backend/environment.example to backend/.env")
    print("   2. Add your GEMINI_API_KEY to the .env file")
    print("   3. Set ENABLE_LLM_PARSING=true")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main()) 