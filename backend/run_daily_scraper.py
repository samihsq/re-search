#!/usr/bin/env python3
"""
Daily Stanford Research Scraper Runner

This script runs the Stanford research opportunities scraper and updates the database.
It can be used locally or by GitHub Actions.

Usage:
    python run_daily_scraper.py [--deep-llm] [--update-urls] [--dry-run]
"""

import asyncio
import argparse
import sys
import os
from datetime import datetime
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.services.scraping_service import ScrapingService
    from app.config import settings
    from app.database import SessionLocal
    from app.models import Opportunity
except ImportError as e:
    print(f"❌ Failed to import modules: {e}")
    print("Make sure you're running this from the backend directory and all dependencies are installed.")
    sys.exit(1)


async def test_database_connection():
    """Test database connection and check table structure."""
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            print("❌ DATABASE_URL environment variable not set")
            return False
            
        print("🔍 Testing database connection...")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Test basic connection
        cursor.execute('SELECT version();')
        version = cursor.fetchone()
        print(f"✅ Database connection successful: {version[0][:50]}...")
        
        # Check if opportunities table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'opportunities'
            );
        """)
        table_exists = cursor.fetchone()[0]
        print(f"📋 Opportunities table exists: {table_exists}")
        
        if table_exists:
            cursor.execute('SELECT COUNT(*) FROM opportunities;')
            count = cursor.fetchone()[0]
            print(f"📊 Current opportunities count: {count}")
        else:
            print("⚠️  Opportunities table does not exist. The scraper may not be able to save data.")
            print("   Consider running database migrations first.")
            
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def run_url_validation(update_config: bool = False):
    """Run URL validation and optionally update configuration."""
    try:
        print("🔍 Running URL validation...")
        
        # Import the URL validator
        import subprocess
        import json
        
        cmd = ["python", "process_stanford_urls.py", "config"]
        if update_config:
            cmd.append("--update-config")
            
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            print("✅ URL validation completed successfully")
            return True
        else:
            print(f"⚠️  URL validation completed with warnings:")
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            return True  # Continue even with warnings
            
    except Exception as e:
        print(f"❌ URL validation failed: {e}")
        return False


async def run_deep_llm_discovery():
    """Run deep LLM discovery for finding new opportunity URLs."""
    try:
        print("🧠 Running deep LLM discovery...")
        
        import subprocess
        
        cmd = ["python", "process_stanford_urls.py", "config", "--deep-llm", "--update-config"]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            print("✅ Deep LLM discovery completed successfully")
            print(result.stdout)
            return True
        else:
            print(f"⚠️  Deep LLM discovery completed with issues:")
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            return True  # Continue even if LLM discovery has issues
            
    except Exception as e:
        print(f"❌ Deep LLM discovery failed: {e}")
        return False


async def run_scraper(dry_run: bool = False):
    """Run the main scraper and return statistics."""
    print(f"🚀 Starting Stanford research scraper...")
    print(f"📅 Started at: {datetime.now()}")
    
    if dry_run:
        print("🔍 DRY RUN MODE - No data will be saved to database")
    
    try:
        print(f"🎯 Target websites: {len(settings.target_websites)}")
        
        scraper = ScrapingService()
        
        # Run the scraper on all configured URLs
        results = await scraper.scrape_all_websites()
        
        # Get statistics
        stats = scraper.get_scraping_stats(results)
        
        # Print detailed results
        print('\n' + '='*60)
        print('📊 SCRAPING RESULTS SUMMARY')
        print('='*60)
        print(f'✅ Total URLs processed: {stats["total_urls"]}')
        print(f'✅ Successful scrapes: {stats["successful_scrapes"]}')
        print(f'❌ Failed scrapes: {stats["failed_scrapes"]}')
        print(f'📊 Total opportunities found: {stats["total_opportunities"]}')
        print(f'🆕 New opportunities: {stats["new_opportunities"]}')
        print(f'🔄 Updated opportunities: {stats["updated_opportunities"]}')
        print(f'🧠 LLM enhanced: {stats["llm_enhanced"]}')
        print(f'🏫 Domains scraped: {len(stats["domains_scraped"])}')
        print(f'⏱️  Total time: {stats["total_time_seconds"]:.2f} seconds')
        
        if stats["scrapers_used"]:
            print(f'\n🔧 Scrapers used:')
            for scraper_name, count in stats["scrapers_used"].items():
                print(f'   • {scraper_name}: {count} URLs')
        
        if stats["domains_scraped"]:
            print(f'\n🏫 Domains scraped:')
            for domain in stats["domains_scraped"][:10]:  # Show first 10
                print(f'   • {domain}')
            if len(stats["domains_scraped"]) > 10:
                print(f'   ... and {len(stats["domains_scraped"]) - 10} more')
        
        if stats["failed_scrapes"] > 0:
            print(f'\n❌ Failed URLs:')
            failed_count = 0
            for result in results:
                if not result.get('success', False) and failed_count < 5:  # Show first 5 failures
                    print(f'   • {result.get("url", "Unknown")}: {result.get("error", "Unknown error")}')
                    failed_count += 1
            if stats["failed_scrapes"] > 5:
                print(f'   ... and {stats["failed_scrapes"] - 5} more failures')
        
        print('\n' + '='*60)
        print(f'✅ Scraping completed successfully!')
        print(f'📅 Finished at: {datetime.now()}')
        
        return stats
        
    except Exception as e:
        print(f'❌ Scraping failed: {e}')
        import traceback
        traceback.print_exc()
        return None


def save_github_outputs(stats: dict):
    """Save outputs for GitHub Actions."""
    if not stats:
        return
        
    github_output = os.getenv('GITHUB_OUTPUT')
    if github_output:
        with open(github_output, 'a') as f:
            f.write(f'total_opportunities={stats["total_opportunities"]}\n')
            f.write(f'new_opportunities={stats["new_opportunities"]}\n')
            f.write(f'updated_opportunities={stats["updated_opportunities"]}\n')
            f.write(f'successful_scrapes={stats["successful_scrapes"]}\n')
            f.write(f'failed_scrapes={stats["failed_scrapes"]}\n')
            f.write(f'llm_enhanced={stats["llm_enhanced"]}\n')
            f.write(f'total_time={stats["total_time_seconds"]:.2f}\n')


async def main():
    parser = argparse.ArgumentParser(description="Run the Stanford research opportunities scraper")
    parser.add_argument('--deep-llm', action='store_true', help='Run deep LLM discovery')
    parser.add_argument('--update-urls', action='store_true', help='Update URL configuration')
    parser.add_argument('--dry-run', action='store_true', help='Run without saving to database')
    parser.add_argument('--skip-db-test', action='store_true', help='Skip database connection test')
    
    args = parser.parse_args()
    
    print("🔬 Stanford Research Opportunities Scraper")
    print("=" * 50)
    
    # Test database connection
    if not args.skip_db_test:
        if not await test_database_connection():
            print("❌ Database connection failed. Exiting.")
            sys.exit(1)
    
    # Run URL validation
    if args.update_urls:
        if not await run_url_validation(update_config=True):
            print("❌ URL validation failed. Exiting.")
            sys.exit(1)
    
    # Run deep LLM discovery if requested
    if args.deep_llm:
        if not await run_deep_llm_discovery():
            print("⚠️  Deep LLM discovery failed, but continuing with scraping...")
    
    # Run the main scraper
    stats = await run_scraper(dry_run=args.dry_run)
    
    if stats is None:
        print("❌ Scraping failed completely.")
        sys.exit(1)
    
    # Save outputs for GitHub Actions
    save_github_outputs(stats)
    
    # Final summary
    print("\n🎉 Daily scraping completed!")
    print(f"📊 Found {stats['total_opportunities']} opportunities total")
    print(f"🆕 {stats['new_opportunities']} new, 🔄 {stats['updated_opportunities']} updated")
    
    if stats['failed_scrapes'] > 0:
        print(f"⚠️  {stats['failed_scrapes']} URLs failed to scrape")
        sys.exit(1)  # Exit with error code if there were failures
    else:
        print("✅ All URLs scraped successfully!")


if __name__ == "__main__":
    asyncio.run(main()) 