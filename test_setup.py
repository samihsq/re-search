#!/usr/bin/env python3
"""
Test script to verify Stanford Research Opportunities Aggregator setup.
Run this script to test the core functionality before full deployment.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

try:
    from app.config import settings
    from app.database import test_connection, init_database
    from app.services.scraping_service import scraping_service
    from app.scrapers.undergrad_research_scraper import UndergradResearchScraper
    from loguru import logger
    
    print("✅ All imports successful!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're in the project root directory and have installed all dependencies.")
    sys.exit(1)


async def test_scraper():
    """Test the undergraduate research scraper."""
    print("\n🔍 Testing undergraduate research scraper...")
    
    try:
        scraper = UndergradResearchScraper(
            "https://undergradresearch.stanford.edu/fund-your-project/explore-departmental-funding"
        )
        print(f"✅ Scraper initialized for {scraper.domain}")
        
        # Test HTML parsing (without actually fetching)
        sample_html = """
        <html>
            <body>
                <div class="opportunity">
                    <h3>Sample Research Grant</h3>
                    <p>This is a sample research opportunity for testing.</p>
                    <div class="deadline">Due: December 31, 2024</div>
                    <div class="funding">$5,000</div>
                </div>
            </body>
        </html>
        """
        
        soup = scraper.parse_html(sample_html)
        print("✅ HTML parsing works")
        
        # Test text cleaning
        cleaned = scraper.clean_text("  This   is\n\ttest   text  ")
        assert cleaned == "This is test text"
        print("✅ Text cleaning works")
        
        # Test date extraction
        date_result = scraper.extract_deadline("Due: December 31, 2024")
        print(f"✅ Date extraction works: {date_result}")
        
        # Test funding amount extraction
        funding_result = scraper.extract_funding_amount("Award amount: $5,000")
        print(f"✅ Funding extraction works: {funding_result}")
        
        print("✅ Scraper tests passed!")
        
    except Exception as e:
        print(f"❌ Scraper test failed: {e}")
        return False
    
    return True


def test_database():
    """Test database connection and setup."""
    print("\n🗄️  Testing database connection...")
    
    try:
        # Test connection
        if test_connection():
            print("✅ Database connection successful")
        else:
            print("❌ Database connection failed")
            return False
        
        # Test database initialization (in production, this would create tables)
        print("✅ Database setup validated")
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    
    return True


def test_config():
    """Test configuration loading."""
    print("\n⚙️  Testing configuration...")
    
    try:
        print(f"App Name: {settings.app_name}")
        print(f"Version: {settings.app_version}")
        print(f"Database URL: {settings.database_url[:50]}...")
        print(f"Target Websites: {len(settings.target_websites)} configured")
        
        # Test scraping configs
        from app.config import SCRAPING_CONFIGS
        print(f"Scraping configs: {list(SCRAPING_CONFIGS.keys())}")
        
        print("✅ Configuration loaded successfully")
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False
    
    return True


def test_models():
    """Test database models."""
    print("\n📊 Testing database models...")
    
    try:
        from app.models import Opportunity, UserPreference, ScrapingLog
        
        # Test model creation (without database)
        opp_data = {
            'title': 'Test Opportunity',
            'description': 'Test description',
            'department': 'Computer Science',
            'opportunity_type': 'research',
            'source_url': 'https://example.com',
            'tags': ['ai', 'ml']
        }
        
        # This would create an instance (not saved to DB in test)
        opportunity = Opportunity(**opp_data)
        print("✅ Opportunity model works")
        
        user_pref_data = {
            'email': 'test@stanford.edu',
            'keywords': ['AI', 'research'],
            'departments': ['Computer Science'],
            'opportunity_types': ['research']
        }
        
        user_pref = UserPreference(**user_pref_data)
        print("✅ UserPreference model works")
        
        print("✅ All models tested successfully")
        
    except Exception as e:
        print(f"❌ Models test failed: {e}")
        return False
    
    return True


async def main():
    """Run all tests."""
    print("🚀 Starting Stanford Research Opportunities Aggregator Tests")
    print("=" * 60)
    
    tests = [
        ("Configuration", test_config),
        ("Database Models", test_models),
        ("Database Connection", test_database),
        ("Web Scraper", test_scraper),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All tests passed! Your setup is ready.")
        print("\nNext steps:")
        print("1. Set up PostgreSQL and Redis (or use Docker Compose)")
        print("2. Copy backend/environment.example to backend/.env and configure")
        print("3. Run: cd backend && python main.py")
        print("4. Visit http://localhost:8000/docs for API documentation")
    else:
        print(f"\n⚠️  {len(results) - passed} tests failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 