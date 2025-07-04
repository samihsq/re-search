from celery import current_task
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Opportunity, ScrapingLog
from ..services.scraping_service import scraping_service
from ..celery_app import celery_app


@celery_app.task(bind=True)
def run_daily_scraping(self):
    """Daily scraping task that runs automatically."""
    logger.info("Starting daily scraping task")
    
    try:
        # Create scraping log entry
        db = SessionLocal()
        scraping_log = ScrapingLog(
            source_url="daily_scraping",
            status="running",
            scraping_started_at=datetime.now()
        )
        db.add(scraping_log)
        db.commit()
        
        # Run scraping
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(scraping_service.scrape_all_urls())
            
            # Calculate statistics
            total_opportunities = sum(r.get('opportunities_found', 0) for r in results if r.get('status') == 'success')
            successful_scrapes = sum(1 for r in results if r.get('status') == 'success')
            failed_scrapes = len(results) - successful_scrapes
            
            # Update scraping log
            scraping_log.status = "completed"
            scraping_log.scraping_completed_at = datetime.now()
            scraping_log.opportunities_found = total_opportunities
            scraping_log.opportunities_new = total_opportunities  # Simplified for now
            db.commit()
            
            logger.success(f"Daily scraping completed: {total_opportunities} opportunities found")
            
            return {
                "status": "success",
                "total_opportunities": total_opportunities,
                "successful_scrapes": successful_scrapes,
                "failed_scrapes": failed_scrapes,
                "results": results
            }
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Daily scraping failed: {e}")
        
        # Update scraping log with error
        if 'scraping_log' in locals():
            scraping_log.status = "failed"
            scraping_log.scraping_completed_at = datetime.now()
            scraping_log.error_message = str(e)
            db.commit()
        
        # Re-raise the exception
        raise
    
    finally:
        if 'db' in locals():
            db.close()


@celery_app.task(bind=True)
def cleanup_old_opportunities(self):
    """Clean up old opportunities that are no longer active."""
    logger.info("Starting cleanup of old opportunities")
    
    try:
        db = SessionLocal()
        
        # Find opportunities older than 6 months that are marked as inactive
        cutoff_date = datetime.now() - timedelta(days=180)
        
        # Count opportunities to be cleaned up
        old_opportunities = db.query(Opportunity).filter(
            Opportunity.scraped_at < cutoff_date,
            Opportunity.is_active == False
        ).count()
        
        # Delete old inactive opportunities
        deleted_count = db.query(Opportunity).filter(
            Opportunity.scraped_at < cutoff_date,
            Opportunity.is_active == False
        ).delete()
        
        db.commit()
        
        logger.info(f"Cleanup completed: {deleted_count} old opportunities removed")
        
        return {
            "status": "success",
            "deleted_count": deleted_count,
            "old_opportunities_found": old_opportunities
        }
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise
    
    finally:
        if 'db' in locals():
            db.close()


@celery_app.task(bind=True)
def scrape_specific_urls(self, urls: list):
    """Task to scrape specific URLs."""
    logger.info(f"Starting scraping for {len(urls)} specific URLs")
    
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(scraping_service.scrape_all_urls(urls))
            
            total_opportunities = sum(r.get('opportunities_found', 0) for r in results if r.get('status') == 'success')
            
            logger.success(f"Specific URL scraping completed: {total_opportunities} opportunities found")
            
            return {
                "status": "success",
                "total_opportunities": total_opportunities,
                "results": results
            }
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Specific URL scraping failed: {e}")
        raise 