import asyncio
from typing import List, Dict, Any, Optional, Type
from datetime import datetime, timedelta
import hashlib
from urllib.parse import urlparse

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from loguru import logger

from ..database import SessionLocal
from ..models import Opportunity, ScrapingLog
from ..config import settings, SCRAPING_CONFIGS
from ..scrapers.base_scraper import BaseScraper
from ..scrapers.undergrad_research_scraper import UndergradResearchScraper
from ..scrapers.stanford_program_scraper import StanfordProgramScraper
from .opportunity_tracking_service import opportunity_tracking_service


class ScrapingService:
    """Service for orchestrating web scraping across multiple Stanford websites."""

    def __init__(self):
        self.scrapers: Dict[str, Type[BaseScraper]] = {
            # Use specialized Stanford program scraper for specific program pages
            "curis.stanford.edu": StanfordProgramScraper,
            "biox.stanford.edu": StanfordProgramScraper,
            "mse.stanford.edu": StanfordProgramScraper,
            "aa.stanford.edu": StanfordProgramScraper,
            "ee.stanford.edu": StanfordProgramScraper,
            "med.stanford.edu": StanfordProgramScraper,
            "biology.stanford.edu": StanfordProgramScraper,
            "solo.stanford.edu": StanfordProgramScraper,
            "siepr.stanford.edu": StanfordProgramScraper,
            "fsi.stanford.edu": StanfordProgramScraper,
            "sgs.stanford.edu": StanfordProgramScraper,
            "careers.stanfordhealthcare.org": StanfordProgramScraper,
            "shc.stanford.edu": StanfordProgramScraper,
            "gender.stanford.edu": StanfordProgramScraper,
            "psychology.stanford.edu": StanfordProgramScraper,
            "physics.stanford.edu": StanfordProgramScraper,
            "msande.stanford.edu": StanfordProgramScraper,
            "linguistics.stanford.edu": StanfordProgramScraper,
            "cee.stanford.edu": StanfordProgramScraper,
            "chemeintranet.stanford.edu": StanfordProgramScraper,
            "neuroscience.stanford.edu": StanfordProgramScraper,
            "sesur.stanford.edu": StanfordProgramScraper,
            "woods.stanford.edu": StanfordProgramScraper,
            "stanfordmicrofluidics.com": StanfordProgramScraper,
            "surim.stanford.edu": StanfordProgramScraper,
            "canarycenter.stanford.edu": StanfordProgramScraper,
            
            # Fallback for other Stanford domains
            "stanford.edu": StanfordProgramScraper,
            
            # Keep the original scraper for general undergraduate research pages
            "undergradresearch.stanford.edu": UndergradResearchScraper,
        }

    def get_scraper(self, url: str) -> BaseScraper:
        """Get the appropriate scraper for a given URL."""
        try:
            domain = urlparse(url).netloc.lower()
            logger.debug(f"Selecting scraper for domain: {domain}")
            
            # Try exact domain match first
            if domain in self.scrapers:
                scraper_class = self.scrapers[domain]
                logger.info(f"Using {scraper_class.__name__} for {domain}")
                return scraper_class(url)
            
            # Try partial domain matches for Stanford sites
            for domain_pattern, scraper_class in self.scrapers.items():
                if domain_pattern in domain:
                    logger.info(f"Using {scraper_class.__name__} for {domain} (matched pattern: {domain_pattern})")
                    return scraper_class(url)
            
            # Default to Stanford program scraper for any Stanford site
            if "stanford" in domain:
                logger.info(f"Using StanfordProgramScraper as default for Stanford domain: {domain}")
                return StanfordProgramScraper(url)
            
            # Final fallback to Stanford program scraper (don't use abstract BaseScraper)
            logger.warning(f"No specific scraper found for {domain}, using StanfordProgramScraper as fallback")
            return StanfordProgramScraper(url)
            
        except Exception as e:
            logger.error(f"Error selecting scraper for {url}: {e}")
            # Always return a concrete scraper, never the abstract base class
            logger.warning("Falling back to StanfordProgramScraper due to error")
            return StanfordProgramScraper(url)

    # ------------------------------------------------------------------
    # Database persistence helper
    # ------------------------------------------------------------------
    def _save_opportunities_to_db(self, opportunities: List[Dict[str, Any]], source_url: str) -> Dict[str, int]:
        """Persist scraped opportunities using advanced tracking and similarity detection.

        This function uses the OpportunityTrackingService to detect duplicates, track changes,
        and maintain opportunity status between scrapes.
        """
        if not opportunities:
            return {"new_count": 0, "updated_count": 0, "missing_count": 0, "reappeared_count": 0}

        # Ensure tags is a list for all opportunities
        for opp in opportunities:
            tags = opp.get("tags") or []
            if isinstance(tags, str):
                try:
                    # Try parsing as JSON first
                    import json
                    tags = json.loads(tags)
                except (json.JSONDecodeError, ValueError):
                    # If not JSON, treat as single tag
                    tags = [tags]
            elif not isinstance(tags, list):
                tags = []
            opp["tags"] = tags

        # Use the tracking service to process opportunities
        try:
            result = opportunity_tracking_service.process_scraped_opportunities(opportunities, source_url)
            logger.info(f"Tracking results for {source_url}: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to process opportunities with tracking for {source_url}: {e}")
            # Fallback to basic counts if tracking fails
            return {"new_count": len(opportunities), "updated_count": 0, "missing_count": 0, "reappeared_count": 0}

    async def scrape_single_url(self, url: str) -> Dict[str, Any]:
        """Scrape a single URL and return results."""
        logger.info(f"Starting scrape for: {url}")
        
        start_time = datetime.now()
        scraper = self.get_scraper(url)
        
        try:
            opportunities = await scraper.scrape()

            # Persist to the database
            stats = self._save_opportunities_to_db(opportunities, url)
            new_count = stats["new_count"]
            updated_count = stats["updated_count"]
            missing_count = stats.get("missing_count", 0)
            reappeared_count = stats.get("reappeared_count", 0)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            result = {
                "url": url,
                "status": "success",
                "opportunities_found": len(opportunities),
                "opportunities": opportunities,
                "new_count": new_count,
                "updated_count": updated_count,
                "missing_count": missing_count,
                "reappeared_count": reappeared_count,
                "scraping_time": duration,
                "scraper_used": scraper.__class__.__name__,
                "domain": urlparse(url).netloc
            }
            
            logger.success(f"Scraped {url}: {len(opportunities)} opportunities found in {duration:.2f}s")
            return result
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.error(f"Failed to scrape {url}: {e}")
            
            return {
                "url": url,
                "status": "error",
                "error": str(e),
                "opportunities_found": 0,
                "opportunities": [],
                "scraping_time": duration,
                "scraper_used": scraper.__class__.__name__,
                "domain": urlparse(url).netloc
            }

    async def scrape_all_urls(self, urls: List[str] = None) -> List[Dict[str, Any]]:
        """Scrape all configured URLs or a custom list of URLs."""
        if urls is None:
            urls = settings.target_websites
        
        logger.info(f"Starting scraping for {len(urls)} URLs")
        
        # Create scraping tasks
        tasks = [self.scrape_single_url(url) for url in urls]
        
        # Execute scraping with concurrency control
        semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
        
        async def scrape_with_semaphore(url):
            async with semaphore:
                return await self.scrape_single_url(url)
        
        # Run all tasks concurrently but with rate limiting
        results = await asyncio.gather(*[scrape_with_semaphore(url) for url in urls], return_exceptions=True)
        
        # Process results
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Exception occurred for URL {urls[i]}: {result}")
                successful_results.append({
                    "url": urls[i],
                    "status": "error",
                    "error": str(result),
                    "opportunities_found": 0,
                    "opportunities": [],
                    "scraping_time": 0,
                    "scraper_used": "Unknown",
                    "domain": urlparse(urls[i]).netloc
                })
            else:
                successful_results.append(result)
        
        # Log summary
        total_opportunities = sum(r.get('opportunities_found', 0) for r in successful_results)
        successful_scrapes = sum(1 for r in successful_results if r.get('status') == 'success')
        failed_scrapes = len(successful_results) - successful_scrapes
        
        logger.info(f"Scraping completed: {successful_scrapes} successful, {failed_scrapes} failed, {total_opportunities} total opportunities")
        
        return successful_results

    async def scrape_all_websites(self, urls: List[str] = None) -> List[Dict[str, Any]]:
        """Scrape all Stanford research websites using the comprehensive RESEARCH_URLS list."""
        if urls is None:
            try:
                from ..config import RESEARCH_URLS
                urls = RESEARCH_URLS
            except ImportError:
                logger.warning("RESEARCH_URLS not found in config, using target_websites")
                urls = settings.target_websites
        
        logger.info(f"Starting comprehensive scraping for {len(urls)} Stanford research URLs")
        return await self.scrape_all_urls(urls)

    async def scrape_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """Scrape all URLs for a specific domain."""
        domain_urls = [url for url in settings.target_websites if domain in url]
        
        if not domain_urls:
            logger.warning(f"No URLs found for domain: {domain}")
            return []
        
        logger.info(f"Scraping {len(domain_urls)} URLs for domain: {domain}")
        return await self.scrape_all_urls(domain_urls)

    def get_scraping_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate statistics from scraping results."""
        if not results:
            return {
                "total_urls": 0,
                "successful_scrapes": 0,
                "failed_scrapes": 0,
                "total_opportunities": 0,
                "new_opportunities": 0,
                "updated_opportunities": 0,
                "llm_enhanced": 0,
                "average_scraping_time": 0,
                "total_time_seconds": 0,
                "domains_scraped": [],
                "scrapers_used": {},
                "success_rate": 0
            }
        
        successful_results = [r for r in results if r.get('status') == 'success']
        failed_results = [r for r in results if r.get('status') == 'error']
        
        domains = list(set(r.get('domain', 'unknown') for r in results))
        scrapers_used = {}
        
        for result in results:
            scraper = result.get('scraper_used', 'Unknown')
            scrapers_used[scraper] = scrapers_used.get(scraper, 0) + 1
        
        total_opportunities = sum(r.get('opportunities_found', 0) for r in successful_results)
        new_opportunities = sum(r.get('new_count', 0) for r in successful_results)
        updated_opportunities = sum(r.get('updated_count', 0) for r in successful_results)
        missing_opportunities = sum(r.get('missing_count', 0) for r in successful_results)
        reappeared_opportunities = sum(r.get('reappeared_count', 0) for r in successful_results)
        
        # Count LLM enhanced opportunities
        llm_enhanced = 0
        for result in successful_results:
            opportunities = result.get('opportunities', [])
            for opp in opportunities:
                if opp.get('llm_parsed', False):
                    llm_enhanced += 1
        
        total_time = sum(r.get('scraping_time', 0) for r in results)
        avg_time = total_time / len(results) if results else 0
        
        return {
            "total_urls": len(results),
            "successful_scrapes": len(successful_results),
            "failed_scrapes": len(failed_results),
            "total_opportunities": total_opportunities,
            "new_opportunities": new_opportunities,
            "updated_opportunities": updated_opportunities,
            "missing_opportunities": missing_opportunities,
            "reappeared_opportunities": reappeared_opportunities,
            "llm_enhanced": llm_enhanced,
            "average_scraping_time": round(avg_time, 2),
            "total_time_seconds": round(total_time, 2),
            "domains_scraped": domains,
            "scrapers_used": scrapers_used,
            "success_rate": round(len(successful_results) / len(results) * 100, 1) if results else 0
        }


# Global scraping service instance
scraping_service = ScrapingService() 