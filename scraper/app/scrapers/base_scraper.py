import asyncio
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin, urlparse
from datetime import datetime, date
import re
import os

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings, SCRAPING_CONFIGS, DEPARTMENT_MAPPING, OPPORTUNITY_TYPE_MAPPING
from ..services.llm_validation_service import llm_parsing_service


class BaseScraper(ABC):
    """Base class for all Stanford website scrapers."""
    
    def __init__(self, url: str, config: Optional[Dict] = None):
        """Initialize the scraper with URL and configuration."""
        self.url = url
        self.domain = urlparse(url).netloc
        self.config = config or SCRAPING_CONFIGS.get(self.domain, {})
        self.session = requests.Session()
        self.driver = None
        
        # Check if Selenium is disabled
        self.selenium_disabled = os.getenv('DISABLE_SELENIUM', '').lower() == 'true'
        
        # Configure session headers
        self.session.headers.update({
            'User-Agent': settings.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        logger.info(f"Initialized scraper for {self.domain}")
    
    def setup_selenium_driver(self) -> Optional[webdriver.Chrome]:
        """Setup and return a Chrome WebDriver instance, or None if not available."""
        if self.selenium_disabled:
            logger.info("Selenium is disabled via environment variable")
            return None
            
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument(f'--user-agent={settings.user_agent}')
        
        try:
            driver = webdriver.Chrome(
                ChromeDriverManager().install(),
                options=chrome_options
            )
            driver.set_page_load_timeout(settings.request_timeout)
            logger.info("Chrome WebDriver initialized successfully")
            return driver
        except Exception as e:
            logger.warning(f"Failed to setup Chrome driver: {e}")
            logger.info("Falling back to requests-only scraping")
            return None
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def fetch_page(self, url: str, use_selenium: bool = False) -> str:
        """Fetch a web page with retry logic."""
        logger.info(f"Fetching page: {url}")
        
        try:
            # Check if Selenium is requested but not available
            if (use_selenium or self.config.get('requires_js', False)) and not self.selenium_disabled:
                selenium_result = self._fetch_with_selenium(url)
                if selenium_result:
                    return selenium_result
                else:
                    logger.warning(f"Selenium failed for {url}, falling back to requests")
            
            # Use requests as fallback or primary method
            return self._fetch_with_requests(url)
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            raise
    
    def _fetch_with_requests(self, url: str) -> str:
        """Fetch page using requests library."""
        response = self.session.get(
            url,
            timeout=settings.request_timeout,
            allow_redirects=True
        )
        response.raise_for_status()
        
        # Add delay to be respectful
        time.sleep(self.config.get('delay', settings.scraping_delay))
        
        return response.text
    
    def _fetch_with_selenium(self, url: str) -> Optional[str]:
        """Fetch page using Selenium WebDriver."""
        if not self.driver:
            self.driver = self.setup_selenium_driver()
            
        if not self.driver:
            logger.warning("Chrome WebDriver not available, cannot use Selenium")
            return None
        
        try:
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Additional wait for dynamic content
            time.sleep(3)
            
            return self.driver.page_source
            
        except TimeoutException:
            logger.warning(f"Timeout loading {url}")
            return self.driver.page_source if self.driver else None
        except WebDriverException as e:
            logger.error(f"WebDriver error for {url}: {e}")
            return None
        finally:
            # Add delay
            time.sleep(self.config.get('delay', settings.scraping_delay))
    
    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content with BeautifulSoup."""
        return BeautifulSoup(html, 'lxml')
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common unwanted characters
        text = re.sub(r'[\r\n\t]', ' ', text)
        
        # Clean up multiple spaces
        text = re.sub(r' +', ' ', text)
        
        return text.strip()
    
    def extract_deadline(self, text: str) -> Optional[date]:
        """Extract deadline date from text."""
        if not text:
            return None
        
        # Common date patterns
        date_patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY
            r'(\d{1,2})-(\d{1,2})-(\d{4})',  # MM-DD-YYYY
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # Month DD, YYYY
            r'(\d{1,2})\s+(\w+)\s+(\d{4})',  # DD Month YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        if groups[0].isdigit() and groups[1].isdigit():
                            # Numeric month/day
                            month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                        else:
                            # Text month
                            from dateutil.parser import parse
                            return parse(match.group()).date()
                        
                        return date(year, month, day)
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def extract_funding_amount(self, text: str) -> Optional[str]:
        """Extract funding amount from text."""
        if not text:
            return None
        
        # Look for dollar amounts
        amount_patterns = [
            r'\$\s?([0-9,]+(?:\.[0-9]{2})?)',  # $1,000.00
            r'([0-9,]+(?:\.[0-9]{2})?)\s?dollars?',  # 1000 dollars
            r'up\s+to\s+\$([0-9,]+)',  # up to $1000
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"${match.group(1)}"
        
        return None
    
    def standardize_department(self, department: str) -> str:
        """Standardize department names."""
        if not department:
            return ""
        
        department_lower = department.lower().strip()
        return DEPARTMENT_MAPPING.get(department_lower, department.title())
    
    def classify_opportunity_type(self, title: str, description: str) -> str:
        """Classify the type of opportunity based on content."""
        content = f"{title} {description}".lower()
        
        for keyword, opp_type in OPPORTUNITY_TYPE_MAPPING.items():
            if keyword in content:
                return opp_type
        
        # Default classification
        if any(word in content for word in ['fund', 'grant', 'award', 'scholarship']):
            return 'funding'
        elif any(word in content for word in ['intern', 'work', 'job']):
            return 'internship'
        else:
            return 'research'
    
    def extract_tags(self, title: str, description: str) -> List[str]:
        """Extract relevant tags from opportunity content."""
        content = f"{title} {description}".lower()
        tags = set()
        
        # Common research areas
        research_areas = [
            'ai', 'artificial intelligence', 'machine learning', 'ml',
            'computer science', 'cs', 'programming', 'software',
            'biology', 'bioinformatics', 'genetics', 'medicine', 'medical',
            'engineering', 'electrical', 'mechanical', 'chemical',
            'physics', 'chemistry', 'mathematics', 'statistics',
            'psychology', 'neuroscience', 'cognitive science',
            'economics', 'business', 'finance', 'marketing',
            'humanities', 'literature', 'history', 'philosophy',
            'environment', 'sustainability', 'climate',
            'data science', 'analytics', 'visualization',
            'robotics', 'automation', 'iot', 'blockchain',
            'healthcare', 'biotech', 'pharma'
        ]
        
        for area in research_areas:
            if area in content:
                tags.add(area)
        
        # Opportunity-specific tags
        if 'summer' in content:
            tags.add('summer program')
        if 'undergraduate' in content:
            tags.add('undergraduate')
        if 'graduate' in content:
            tags.add('graduate')
        if 'international' in content:
            tags.add('international')
        if 'remote' in content:
            tags.add('remote')
        
        return list(tags)
    
    @abstractmethod
    def extract_opportunities(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract opportunities from parsed HTML. Must be implemented by subclasses."""
        pass
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """Main scraping method with LLM HTML parsing."""
        logger.info(f"Starting scrape of {self.url}")
        
        try:
            # Fetch the page
            html = self.fetch_page(self.url)
            
            # Use LLM HTML parsing if enabled, otherwise fall back to traditional scraping
            if settings.enable_llm_parsing and settings.gemini_api_key:
                logger.info("Using LLM HTML parsing for opportunity extraction...")
                
                try:
                    parse_result = await llm_parsing_service.parse_html_content(html, self.url)
                    
                    if parse_result.get("success"):
                        llm_opportunities = parse_result.get("opportunities", [])
                        logger.success(f"LLM HTML parsing extracted {len(llm_opportunities)} opportunities")
                        
                        # Convert to our expected format and add metadata
                        opportunities = []
                        for opp_data in llm_opportunities:
                            opportunity = {
                                'title': opp_data.get('title', ''),
                                'description': opp_data.get('description', ''),
                                'tags': opp_data.get('tags', []),
                                'deadline': opp_data.get('deadline'),
                                'funding_amount': opp_data.get('funding_amount'),
                                'application_url': opp_data.get('application_url') or self.url,
                                'contact_email': opp_data.get('contact_email'),
                                'eligibility_requirements': opp_data.get('eligibility_requirements'),
                                'department': opp_data.get('department', ''),
                                'opportunity_type': opp_data.get('opportunity_type', 'research'),
                                'source_url': self.url,
                                'scraped_at': datetime.now().isoformat(),
                                'llm_parsed': True,
                                'scraper_used': self.__class__.__name__
                            }
                            opportunities.append(opportunity)
                        
                        return opportunities
                    else:
                        error_msg = parse_result.get("error", "unknown_error")
                        logger.warning(f"LLM HTML parsing failed: {error_msg}. Falling back to traditional scraping.")
                     
                except Exception as e:
                    logger.error(f"LLM HTML parsing failed with exception: {e}")
                    logger.info("Falling back to traditional scraping")
            
            # Traditional scraping fallback
            logger.info("Using traditional scraping method...")
            
            # Parse HTML
            soup = self.parse_html(html)
            
            # Extract opportunities using the subclass implementation
            extract_method = self.extract_opportunities(soup)
            if asyncio.iscoroutine(extract_method):
                opportunities = await extract_method
            else:
                opportunities = extract_method
            
            # Add metadata for traditional scraping
            for opp in opportunities:
                opp.update({
                    'source_url': self.url,
                    'scraped_at': datetime.now().isoformat(),
                    'llm_parsed': False,
                    'scraper_used': self.__class__.__name__
                })
            
            logger.info(f"Traditional scraping extracted {len(opportunities)} opportunities from {self.domain}")
             
            # Clean up
            if self.driver:
                self.driver.quit()
                self.driver = None
             
            logger.info(f"Final output: {len(opportunities)} opportunities from {self.domain}")
            return opportunities
            
        except Exception as e:
            logger.error(f"Scraping failed for {self.url}: {e}")
            if self.driver:
                self.driver.quit()
                self.driver = None
            raise
    
    def __del__(self):
        """Cleanup method."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass 