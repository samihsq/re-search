#!/usr/bin/env python3
"""
URL Validation Script for Stanford Research URLs

This script tests all URLs in the RESEARCH_URLS list to:
1. Check for 404s and connectivity issues
2. Validate that URLs return useful research opportunity data
3. Identify URLs with multiple opportunities that need more specific sub-pages
4. Generate a report with recommendations
"""

import asyncio
import aiohttp
import json
import sys
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict
from datetime import datetime

# Add the app directory to the path
sys.path.append('./backend')
from app.config import RESEARCH_URLS
from app.services.scraping_service import ScrapingService


@dataclass
class URLTestResult:
    """Result of testing a single URL."""
    url: str
    status: str  # 'success', 'error', 'redirect', '404', 'timeout'
    status_code: Optional[int] = None
    redirect_url: Optional[str] = None
    response_time: float = 0.0
    content_length: int = 0
    has_research_keywords: bool = False
    opportunities_found: int = 0
    error_message: Optional[str] = None
    recommendations: List[str] = None
    sub_urls: List[str] = None
    
    def __post_init__(self):
        if self.recommendations is None:
            self.recommendations = []
        if self.sub_urls is None:
            self.sub_urls = []


class URLValidator:
    """Validates and analyzes Stanford research URLs."""
    
    def __init__(self):
        self.scraping_service = ScrapingService()
        self.session = None
        self.research_keywords = [
            'research', 'internship', 'fellowship', 'opportunity', 'program',
            'undergraduate', 'student', 'apply', 'application', 'summer',
            'REU', 'SURF', 'UROP', 'position', 'opening', 'lab', 'faculty'
        ]
    
    async def __aenter__(self):
        """Async context manager entry."""
        timeout = aiohttp.ClientTimeout(total=10, connect=5)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; Stanford Research Scraper; contact@stanford.edu)'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def test_url_connectivity(self, url: str) -> URLTestResult:
        """Test basic connectivity and response for a URL."""
        result = URLTestResult(url=url, status='unknown')
        start_time = time.time()
        
        try:
            async with self.session.get(url, allow_redirects=True) as response:
                result.response_time = time.time() - start_time
                result.status_code = response.status
                result.content_length = len(await response.text())
                
                if response.status == 200:
                    result.status = 'success'
                    if str(response.url) != url:
                        result.redirect_url = str(response.url)
                        result.status = 'redirect'
                elif response.status == 404:
                    result.status = '404'
                elif response.status >= 400:
                    result.status = 'error'
                    result.error_message = f"HTTP {response.status}"
                else:
                    result.status = 'success'
                    
        except asyncio.TimeoutError:
            result.status = 'timeout'
            result.error_message = 'Request timeout'
            result.response_time = time.time() - start_time
        except Exception as e:
            result.status = 'error'
            result.error_message = str(e)
            result.response_time = time.time() - start_time
        
        return result
    
    async def test_url_content(self, url: str) -> URLTestResult:
        """Test URL content for research opportunities."""
        result = await self.test_url_connectivity(url)
        
        if result.status not in ['success', 'redirect']:
            return result
        
        try:
            # Test with scraping service
            scraping_result = await self.scraping_service.scrape_single_url(url)
            result.opportunities_found = scraping_result.get('opportunities_found', 0)
            
            # Analyze content for research keywords
            async with self.session.get(url) as response:
                if response.status == 200:
                    text = await response.text()
                    result.has_research_keywords = self._has_research_keywords(text)
                    
                    # Find potential sub-URLs for pages with multiple opportunities
                    if result.opportunities_found > 2:
                        result.sub_urls = await self._find_sub_urls(url, text)
                        if result.sub_urls:
                            result.recommendations.append(
                                f"Found {len(result.sub_urls)} potential sub-pages for more specific scraping"
                            )
                    
                    # Add recommendations based on results
                    if result.opportunities_found == 0:
                        if result.has_research_keywords:
                            result.recommendations.append("Contains research keywords but no opportunities extracted - may need custom scraper")
                        else:
                            result.recommendations.append("No research content found - consider removing")
                    elif result.opportunities_found > 5:
                        result.recommendations.append("High opportunity count - look for more specific sub-pages")
        
        except Exception as e:
            result.error_message = f"Content analysis failed: {str(e)}"
        
        return result
    
    def _has_research_keywords(self, text: str) -> bool:
        """Check if text contains research-related keywords."""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.research_keywords)
    
    async def _find_sub_urls(self, base_url: str, html: str) -> List[str]:
        """Find potential sub-URLs that might contain more specific opportunities."""
        soup = BeautifulSoup(html, 'html.parser')
        base_domain = urlparse(base_url).netloc
        sub_urls = set()
        
        # Look for links that might contain opportunities
        opportunity_patterns = [
            'application', 'apply', 'program', 'opportunity', 'internship',
            'fellowship', 'research', 'undergraduate', 'student', 'position'
        ]
        
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if not href:
                continue
            
            # Convert relative URLs to absolute
            full_url = urljoin(base_url, href)
            
            # Only include URLs from the same domain
            if urlparse(full_url).netloc != base_domain:
                continue
            
            # Check if link text or URL contains opportunity keywords
            link_text = link.get_text().lower()
            href_lower = href.lower()
            
            if any(pattern in link_text or pattern in href_lower for pattern in opportunity_patterns):
                sub_urls.add(full_url)
        
        return list(sub_urls)[:10]  # Limit to 10 most relevant
    
    async def validate_all_urls(self, urls: List[str] = None) -> List[URLTestResult]:
        """Validate all URLs in the research list."""
        if urls is None:
            urls = RESEARCH_URLS
        
        print(f"Starting validation of {len(urls)} URLs...")
        
        # Test connectivity first (faster)
        print("Step 1: Testing connectivity...")
        connectivity_results = await asyncio.gather(
            *[self.test_url_connectivity(url) for url in urls],
            return_exceptions=True
        )
        
        # Filter successful URLs for content testing
        successful_urls = []
        all_results = []
        
        for i, result in enumerate(connectivity_results):
            if isinstance(result, Exception):
                error_result = URLTestResult(
                    url=urls[i], 
                    status='error', 
                    error_message=str(result)
                )
                all_results.append(error_result)
            else:
                all_results.append(result)
                if result.status in ['success', 'redirect']:
                    successful_urls.append(result.url)
        
        # Test content for successful URLs
        if successful_urls:
            print(f"Step 2: Testing content for {len(successful_urls)} successful URLs...")
            content_results = await asyncio.gather(
                *[self.test_url_content(url) for url in successful_urls],
                return_exceptions=True
            )
            
            # Update results with content analysis
            content_results_dict = {}
            for i, result in enumerate(content_results):
                if not isinstance(result, Exception):
                    content_results_dict[successful_urls[i]] = result
            
            # Replace connectivity results with content results where available
            for i, result in enumerate(all_results):
                if result.url in content_results_dict:
                    all_results[i] = content_results_dict[result.url]
        
        return all_results
    
    def generate_report(self, results: List[URLTestResult]) -> Dict[str, Any]:
        """Generate a comprehensive report from validation results."""
        total_urls = len(results)
        successful = len([r for r in results if r.status in ['success', 'redirect']])
        errors = len([r for r in results if r.status == 'error'])
        timeouts = len([r for r in results if r.status == 'timeout'])
        not_found = len([r for r in results if r.status == '404'])
        
        # URLs to remove (problematic)
        urls_to_remove = [
            r.url for r in results 
            if r.status in ['404', 'timeout'] or 
            (r.status == 'error' and 'certificate' not in (r.error_message or '').lower()) or
            (r.status == 'success' and r.opportunities_found == 0 and not r.has_research_keywords)
        ]
        
        # URLs with multiple opportunities (candidates for sub-URL extraction)
        high_opportunity_urls = [
            r for r in results 
            if r.opportunities_found > 2 and r.status in ['success', 'redirect']
        ]
        
        # Recommended sub-URLs to add
        sub_urls_to_add = []
        for result in high_opportunity_urls:
            if result.sub_urls:
                sub_urls_to_add.extend(result.sub_urls)
        
        return {
            'summary': {
                'total_urls': total_urls,
                'successful': successful,
                'errors': errors,
                'timeouts': timeouts,
                'not_found': not_found,
                'success_rate': f"{(successful/total_urls)*100:.1f}%"
            },
            'actions': {
                'urls_to_remove': urls_to_remove,
                'urls_to_replace_with_specific': [r.url for r in high_opportunity_urls if r.sub_urls],
                'sub_urls_to_add': list(set(sub_urls_to_add))[:50]  # Limit to 50 best candidates
            },
            'detailed_results': [asdict(r) for r in results]
        }


async def main():
    """Main function to run URL validation."""
    async with URLValidator() as validator:
        results = await validator.validate_all_urls()
        report = validator.generate_report(results)
        
        # Save report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"url_validation_report_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\n" + "="*50)
        print("URL VALIDATION REPORT")
        print("="*50)
        print(f"Total URLs tested: {report['summary']['total_urls']}")
        print(f"Successful: {report['summary']['successful']}")
        print(f"Errors: {report['summary']['errors']}")
        print(f"Timeouts: {report['summary']['timeouts']}")
        print(f"404 Not Found: {report['summary']['not_found']}")
        print(f"Success Rate: {report['summary']['success_rate']}")
        print()
        print(f"URLs to remove: {len(report['actions']['urls_to_remove'])}")
        print(f"URLs to replace with specific pages: {len(report['actions']['urls_to_replace_with_specific'])}")
        print(f"New sub-URLs to add: {len(report['actions']['sub_urls_to_add'])}")
        print()
        print(f"Detailed report saved to: {report_file}")
        
        # Show some examples
        if report['actions']['urls_to_remove']:
            print("\nSample URLs to remove:")
            for url in report['actions']['urls_to_remove'][:5]:
                print(f"  - {url}")
        
        if report['actions']['sub_urls_to_add']:
            print("\nSample new URLs to add:")
            for url in report['actions']['sub_urls_to_add'][:5]:
                print(f"  + {url}")


if __name__ == "__main__":
    asyncio.run(main()) 