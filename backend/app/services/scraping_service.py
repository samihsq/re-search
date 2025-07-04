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
        domain = urlparse(url).netloc.lower()
        
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
        
        # Final fallback to base scraper
        logger.warning(f"No specific scraper found for {domain}, using BaseScraper")
        return BaseScraper(url)

    # ------------------------------------------------------------------
    # Database persistence helper
    # ------------------------------------------------------------------
    def _save_opportunities_to_db(self, opportunities: List[Dict[str, Any]], source_url: str) -> Dict[str, int]:
        """Persist scraped (and optionally LLM-enhanced) opportunities.

        The function performs a simple upsert keyed by (title, source_url).
        It returns a dictionary with counts of new and updated rows so the
        caller can surface accurate metrics.
        """
        new_count = 0
        updated_count = 0

        if not opportunities:
            return {"new_count": 0, "updated_count": 0}

        db: Session = SessionLocal()
        try:
            for opp in opportunities:
                title = (opp.get("title") or "").strip()
                if not title:
                    continue  # skip malformed entries without a title

                existing = (
                    db.query(Opportunity)
                    .filter(
                        Opportunity.title == title,
                        Opportunity.source_url == source_url,
                    )
                    .first()
                )

                # Ensure tags is a list for JSON column
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

                opportunity = Opportunity(
                    title=opp.get("title") or "Untitled",
                    description=opp.get("description") or "",
                    department=opp.get("department") or "",
                    opportunity_type=opp.get("opportunity_type") or "research",
                    eligibility_requirements=opp.get("eligibility_requirements"),
                    deadline=opp.get("deadline"),
                    funding_amount=opp.get("funding_amount"),
                    application_url=opp.get("application_url") or source_url,
                    source_url=source_url,
                    contact_email=opp.get("contact_email"),
                    tags=tags,
                    
                    # LLM-related metadata
                    llm_parsed=opp.get("llm_parsed", False),
                    parsing_confidence=opp.get("parsing_confidence"),
                    scraper_used=opp.get("scraper_used"),
                    llm_error=opp.get("llm_error"),
                    processed_at=opp.get("processed_at"),
                    
                    # Standard metadata
                    scraped_at=opp.get("scraped_at") or datetime.now(),
                    is_active=True
                )

                if existing:
                    # Update selected fields only if new data is present
                    existing.description = opp.get("description", existing.description)
                    existing.department = opp.get("department", existing.department)
                    existing.opportunity_type = opp.get("opportunity_type", existing.opportunity_type)
                    existing.eligibility_requirements = opp.get(
                        "eligibility_requirements", existing.eligibility_requirements
                    )
                    existing.deadline = opp.get("deadline", existing.deadline)
                    existing.funding_amount = opp.get("funding_amount", existing.funding_amount)
                    existing.application_url = opp.get("application_url", existing.application_url)
                    existing.contact_email = opp.get("contact_email", existing.contact_email)
                    existing.tags = tags or existing.tags

                    # LLM parsing metadata
                    existing.llm_parsed = opp.get("llm_parsed", existing.llm_parsed)
                    existing.parsing_confidence = opp.get("parsing_confidence", existing.parsing_confidence)
                    existing.scraper_used = opp.get("scraper_used", existing.scraper_used)
                    existing.llm_error = opp.get("llm_error", existing.llm_error)
                    existing.processed_at = opp.get("processed_at", existing.processed_at)
                    existing.scraped_at = datetime.now()
                    existing.is_active = True

                    updated_count += 1
                else:
                    db.add(opportunity)
                    new_count += 1

            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save opportunities for {source_url}: {e}")
        finally:
            db.close()

        return {"new_count": new_count, "updated_count": updated_count}

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

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            result = {
                "url": url,
                "status": "success",
                "opportunities_found": len(opportunities),
                "opportunities": opportunities,
                "new_count": new_count,
                "updated_count": updated_count,
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
            from ..config import RESEARCH_URLS
            urls = RESEARCH_URLS
        
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
                "average_scraping_time": 0,
                "domains_scraped": [],
                "scrapers_used": {}
            }
        
        successful_results = [r for r in results if r.get('status') == 'success']
        failed_results = [r for r in results if r.get('status') == 'error']
        
        domains = list(set(r.get('domain', 'unknown') for r in results))
        scrapers_used = {}
        
        for result in results:
            scraper = result.get('scraper_used', 'Unknown')
            scrapers_used[scraper] = scrapers_used.get(scraper, 0) + 1
        
        total_opportunities = sum(r.get('opportunities_found', 0) for r in successful_results)
        total_time = sum(r.get('scraping_time', 0) for r in results)
        avg_time = total_time / len(results) if results else 0
        
        return {
            "total_urls": len(results),
            "successful_scrapes": len(successful_results),
            "failed_scrapes": len(failed_results),
            "total_opportunities": total_opportunities,
            "average_scraping_time": round(avg_time, 2),
            "total_scraping_time": round(total_time, 2),
            "domains_scraped": domains,
            "scrapers_used": scrapers_used,
            "success_rate": round(len(successful_results) / len(results) * 100, 1) if results else 0
        }


# Global scraping service instance
scraping_service = ScrapingService() 