from typing import List, Dict, Any
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin, urlparse
import re
import asyncio
import aiohttp

from .base_scraper import BaseScraper
from loguru import logger


class StanfordProgramScraper(BaseScraper):
    """Aggressive scraper for Stanford research programs that digs deep to find specific opportunities with application links."""
    
    def __init__(self, url: str):
        super().__init__(url)
        self.explored_urls = set()  # Track explored URLs to avoid infinite loops
        self.max_depth = 2  # Maximum depth to explore
        self.user_agent = self.session.headers.get('User-Agent', 'Stanford Research Bot/1.0')  # Fix user_agent issue
        
    async def extract_opportunities(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract specific research opportunities by aggressively searching for actionable content."""
        opportunities = []
        
        try:
            logger.info(f"Starting aggressive opportunity extraction for {self.domain}")
            
            # Step 1: Look for direct opportunities on current page
            direct_opportunities = self._extract_direct_opportunities(soup)
            opportunities.extend(direct_opportunities)
            
            # Step 2: Find and follow links to application pages, specific programs, etc.
            sub_page_opportunities = await self._extract_from_sub_pages(soup)
            opportunities.extend(sub_page_opportunities)
            
            # Step 3: Look for embedded forms, documents, or hidden content
            embedded_opportunities = self._extract_embedded_opportunities(soup)
            opportunities.extend(embedded_opportunities)
            
            # Step 4: Extract from tables, lists, and structured content
            structured_opportunities = self._extract_from_structured_content(soup)
            opportunities.extend(structured_opportunities)
            
            # Remove duplicates and filter out low-quality results
            opportunities = self._filter_and_deduplicate_opportunities(opportunities)
            
        except Exception as e:
            logger.error(f"Error in aggressive opportunity extraction: {e}")
        
        logger.info(f"Extracted {len(opportunities)} actionable opportunities from {self.domain}")
        return opportunities
    
    def _extract_direct_opportunities(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract opportunities directly visible on the current page."""
        opportunities = []
        
        try:
            # Look for opportunity-specific content blocks
            opportunity_selectors = [
                '.opportunity', '.program', '.position', '.internship',
                '.research-project', '.project', '.fellowship',
                '.vacancy', '.opening', '.application', '.deadline',
                '[class*="opportunity"]', '[class*="program"]', '[class*="apply"]',
                '.content', '.main-content', '.page-content'  # Add broader selectors
            ]
            
            for selector in opportunity_selectors:
                elements = soup.select(selector)
                for element in elements:
                    opp = self._extract_opportunity_from_element(element)
                    if self._is_valid_opportunity(opp):
                        opportunities.append(opp)
            
            # Look for deadline mentions that indicate real opportunities
            deadline_blocks = self._find_deadline_blocks(soup)
            for block in deadline_blocks:
                opp = self._extract_opportunity_from_deadline_block(block)
                if self._is_valid_opportunity(opp):
                    opportunities.append(opp)
            
            # Look for application links that indicate real opportunities
            app_link_blocks = self._find_application_link_blocks(soup)
            for block in app_link_blocks:
                opp = self._extract_opportunity_from_app_link_block(block)
                if self._is_valid_opportunity(opp):
                    opportunities.append(opp)
            
            # NEW: Look for prominent application buttons/links anywhere on page
            self._extract_prominent_application_links(soup, opportunities)
            
            # NEW: Look for deadline text anywhere on page
            self._extract_deadline_text_anywhere(soup, opportunities)
                     
        except Exception as e:
            logger.error(f"Error extracting direct opportunities: {e}")
        
        return opportunities
    
    async def _extract_from_sub_pages(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Follow links to find opportunities on sub-pages."""
        opportunities = []
        
        try:
            # Find promising links to follow
            promising_links = self._find_promising_links(soup)
            
            logger.info(f"Found {len(promising_links)} promising links to explore")
            
            # Limit concurrent requests to avoid overwhelming servers
            semaphore = asyncio.Semaphore(2)
            
            async def scrape_sub_page(link_info):
                async with semaphore:
                    return await self._scrape_sub_page(link_info)
            
            # Scrape sub-pages concurrently
            if promising_links:
                sub_page_results = await asyncio.gather(
                    *[scrape_sub_page(link) for link in promising_links[:5]],  # Limit to 5 sub-pages
                    return_exceptions=True
                )
                
                for result in sub_page_results:
                    if isinstance(result, list):
                        opportunities.extend(result)
                        
        except Exception as e:
            logger.error(f"Error extracting from sub-pages: {e}")
        
        return opportunities
    
    def _extract_embedded_opportunities(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract opportunities from embedded content like iframes, scripts, or hidden elements."""
        opportunities = []
        
        try:
            # Look for iframes that might contain application forms
            iframes = soup.select('iframe')
            for iframe in iframes:
                src = iframe.get('src')
                if src and any(keyword in src.lower() for keyword in ['apply', 'form', 'application']):
                    opp = {
                        'title': f"Application Form - {self._determine_department()}",
                        'description': f"Online application form for {self._determine_department()} programs",
                        'application_url': urljoin(self.url, src),
                        'source_url': self.url,
                        'department': self._determine_department(),
                        'opportunity_type': 'research',
                        'tags': ['application', 'form']
                    }
                    opportunities.append(opp)
            
            # Look for JavaScript-embedded content
            scripts = soup.select('script')
            for script in scripts:
                if script.string:
                    # Look for embedded URLs or data
                    urls = re.findall(r'https?://[^\s"\'<>]+(?:apply|application|form)', script.string)
                    for url in urls:
                        opp = {
                            'title': f"Embedded Application - {self._determine_department()}",
                            'description': f"Application link found in page scripts",
                            'application_url': url,
                            'source_url': self.url,
                            'department': self._determine_department(),
                            'opportunity_type': 'research',
                            'tags': ['embedded', 'application']
                        }
                        opportunities.append(opp)
                        
        except Exception as e:
            logger.error(f"Error extracting embedded opportunities: {e}")
        
        return opportunities
    
    def _extract_from_structured_content(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract opportunities from tables, lists, and other structured content."""
        opportunities = []
        
        try:
            # Extract from tables
            tables = soup.select('table')
            for table in tables:
                table_opportunities = self._extract_from_table(table)
                opportunities.extend(table_opportunities)
            
            # Extract from lists
            lists = soup.select('ul, ol')
            for list_elem in lists:
                list_opportunities = self._extract_from_list(list_elem)
                opportunities.extend(list_opportunities)
            
            # Extract from definition lists (often used for program details)
            dl_elements = soup.select('dl')
            for dl in dl_elements:
                dl_opportunities = self._extract_from_definition_list(dl)
                opportunities.extend(dl_opportunities)
                
        except Exception as e:
            logger.error(f"Error extracting from structured content: {e}")
        
        return opportunities
    
    def _find_promising_links(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Find links that are likely to contain specific opportunities."""
        promising_links = []
        
        # Keywords that indicate promising links
        promising_keywords = [
            'apply', 'application', 'deadline', 'form', 'submit',
            'opportunity', 'position', 'internship', 'fellowship',
            'program', 'research', 'project', 'stipend', 'funding'
        ]
        
        links = soup.select('a[href]')
        for link in links:
            href = link.get('href')
            text = link.get_text(strip=True).lower()
            title = link.get('title', '').lower()
            
            if href and not href.startswith('mailto:'):
                # Check if link text or title contains promising keywords
                if any(keyword in text or keyword in title for keyword in promising_keywords):
                    full_url = urljoin(self.url, href)
                    
                    # Only follow Stanford links
                    if 'stanford' in full_url and full_url not in self.explored_urls:
                        promising_links.append({
                            'url': full_url,
                            'text': link.get_text(strip=True),
                            'context': text
                        })
        
        return promising_links[:10]  # Limit to top 10 most promising
    
    async def _scrape_sub_page(self, link_info: Dict[str, str]) -> List[Dict[str, Any]]:
        """Scrape a sub-page for opportunities."""
        opportunities = []
        url = link_info['url']
        
        if url in self.explored_urls:
            return opportunities
        
        self.explored_urls.add(url)
        
        try:
            logger.info(f"Exploring sub-page: {url}")
            
            # Fetch the sub-page
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers={'User-Agent': self.user_agent}) as response:
                    if response.status == 200:
                        content = await response.text()
                        sub_soup = BeautifulSoup(content, 'html.parser')
                        
                        # Look for specific application forms or deadlines
                        opportunities = self._extract_specific_content_from_subpage(sub_soup, url, link_info)
                        
        except Exception as e:
            logger.error(f"Error scraping sub-page {url}: {e}")
        
        return opportunities
    
    def _extract_specific_content_from_subpage(self, soup: BeautifulSoup, url: str, link_info: Dict[str, str]) -> List[Dict[str, Any]]:
        """Extract specific, actionable content from a sub-page."""
        opportunities = []
        
        # Look for application forms
        forms = soup.select('form')
        for form in forms:
            action = form.get('action')
            if action:
                full_action_url = urljoin(url, action)
                opp = {
                    'title': f"{link_info['text']} - Application Form",
                    'description': f"Direct application form for {link_info['text']}",
                    'application_url': full_action_url,
                    'source_url': url,
                    'department': self._determine_department(),
                    'opportunity_type': self._classify_from_text(link_info['text']),
                    'tags': ['application', 'form', 'direct']
                }
                opportunities.append(opp)
        
        # Look for deadlines on this page
        deadline_text = self._extract_deadline_from_page(soup)
        if deadline_text:
            deadline = self.extract_deadline(deadline_text)
            if deadline:
                opp = {
                    'title': link_info['text'],
                    'description': f"Research opportunity with specific deadline: {deadline_text}",
                    'application_url': url,
                    'deadline': deadline,
                    'source_url': url,
                    'department': self._determine_department(),
                    'opportunity_type': self._classify_from_text(link_info['text']),
                    'tags': ['deadline', 'specific']
                }
                opportunities.append(opp)
        
        # Look for funding information
        funding_text = self._extract_funding_from_page(soup)
        if funding_text:
            funding_amount = self.extract_funding_amount(funding_text)
            if funding_amount:
                opp = {
                    'title': link_info['text'],
                    'description': f"Funded research opportunity: {funding_text}",
                    'application_url': url,
                    'funding_amount': funding_amount,
                    'source_url': url,
                    'department': self._determine_department(),
                    'opportunity_type': self._classify_from_text(link_info['text']),
                    'tags': ['funded', 'specific']
                }
                opportunities.append(opp)
        
        return opportunities
    
    def _find_deadline_blocks(self, soup: BeautifulSoup) -> List[Tag]:
        """Find content blocks that mention deadlines."""
        deadline_blocks = []
        
        # Look for elements containing deadline keywords
        deadline_keywords = ['deadline', 'due date', 'apply by', 'application due', 'submit by']
        
        for keyword in deadline_keywords:
            elements = soup.find_all(text=re.compile(keyword, re.IGNORECASE))
            for element in elements:
                parent = element.parent
                if parent and parent not in deadline_blocks:
                    deadline_blocks.append(parent)
        
        return deadline_blocks
    
    def _find_application_link_blocks(self, soup: BeautifulSoup) -> List[Tag]:
        """Find content blocks that contain application links."""
        app_blocks = []
        
        # Look for links with application-related text
        app_links = soup.select('a[href*="apply"], a[href*="application"], a[href*="form"]')
        for link in app_links:
            # Get the surrounding context
            parent = link.parent
            while parent and parent.name not in ['div', 'section', 'article', 'li']:
                parent = parent.parent
            if parent and parent not in app_blocks:
                app_blocks.append(parent)
        
        return app_blocks
    
    def _extract_opportunity_from_deadline_block(self, block: Tag) -> Dict[str, Any]:
        """Extract opportunity information from a block that mentions deadlines."""
        text = block.get_text(strip=True)
        
        # Extract deadline
        deadline_text = self._extract_deadline_text_from_block(text)
        deadline = self.extract_deadline(deadline_text) if deadline_text else None
        
        # Look for application links in this block
        app_links = block.select('a[href]')
        app_url = ""
        for link in app_links:
            href = link.get('href')
            if href and any(keyword in href.lower() for keyword in ['apply', 'application', 'form']):
                app_url = urljoin(self.url, href)
                break
        
        # Extract title from heading or strong text in block
        title = self._extract_title_from_block(block)
        
        return {
            'title': title or f"Research Opportunity with Deadline",
            'description': text[:300] + "..." if len(text) > 300 else text,
            'deadline': deadline,
            'application_url': app_url,
            'source_url': self.url,
            'department': self._determine_department(),
            'opportunity_type': 'research',
            'tags': ['deadline', 'time-sensitive']
        }
    
    def _extract_opportunity_from_app_link_block(self, block: Tag) -> Dict[str, Any]:
        """Extract opportunity information from a block that contains application links."""
        text = block.get_text(strip=True)
        
        # Find the application link
        app_links = block.select('a[href]')
        app_url = ""
        link_text = ""
        
        for link in app_links:
            href = link.get('href')
            if href and any(keyword in href.lower() for keyword in ['apply', 'application', 'form']):
                app_url = urljoin(self.url, href)
                link_text = link.get_text(strip=True)
                break
        
        # Extract title
        title = self._extract_title_from_block(block) or link_text
        
        return {
            'title': title or f"Application Available",
            'description': text[:300] + "..." if len(text) > 300 else text,
            'application_url': app_url,
            'source_url': self.url,
            'department': self._determine_department(),
            'opportunity_type': self._classify_from_text(text),
            'tags': ['application', 'direct-link']
        }
    
    def _extract_from_table(self, table: Tag) -> List[Dict[str, Any]]:
        """Extract opportunities from table data."""
        opportunities = []
        
        try:
            rows = table.select('tr')
            headers = []
            
            # Get headers
            header_row = table.select_one('thead tr, tr:first-child')
            if header_row:
                headers = [th.get_text(strip=True).lower() for th in header_row.select('th, td')]
            
            # Process data rows
            for row in rows[1:] if headers else rows:
                cells = row.select('td, th')
                if len(cells) >= 2:  # Need at least 2 columns for meaningful data
                    row_data = [cell.get_text(strip=True) for cell in cells]
                    
                    # Look for application links in this row
                    app_links = row.select('a[href]')
                    app_url = ""
                    for link in app_links:
                        href = link.get('href')
                        if href and any(keyword in href.lower() for keyword in ['apply', 'application']):
                            app_url = urljoin(self.url, href)
                            break
                    
                    if app_url or any('deadline' in cell.lower() for cell in row_data):
                        opp = {
                            'title': row_data[0] if row_data else "Table Opportunity",
                            'description': " | ".join(row_data),
                            'application_url': app_url,
                            'source_url': self.url,
                            'department': self._determine_department(),
                            'opportunity_type': 'research',
                            'tags': ['table', 'structured']
                        }
                        
                        # Try to extract deadline from row data
                        for cell in row_data:
                            deadline = self.extract_deadline(cell)
                            if deadline:
                                opp['deadline'] = deadline
                                break
                        
                        opportunities.append(opp)
                        
        except Exception as e:
            logger.error(f"Error extracting from table: {e}")
        
        return opportunities
    
    def _extract_from_list(self, list_elem: Tag) -> List[Dict[str, Any]]:
        """Extract opportunities from list elements."""
        opportunities = []
        
        try:
            items = list_elem.select('li')
            for item in items:
                item_text = item.get_text(strip=True)
                
                # Look for application links
                app_links = item.select('a[href]')
                app_url = ""
                for link in app_links:
                    href = link.get('href')
                    if href and any(keyword in href.lower() for keyword in ['apply', 'application', 'form']):
                        app_url = urljoin(self.url, href)
                        break
                
                # Check if this list item contains opportunity-relevant information
                if (app_url or 
                    any(keyword in item_text.lower() for keyword in 
                        ['deadline', 'apply', 'application', 'opportunity', 'position', 'internship'])):
                    
                    opp = {
                        'title': item_text[:100] + "..." if len(item_text) > 100 else item_text,
                        'description': item_text,
                        'application_url': app_url,
                        'source_url': self.url,
                        'department': self._determine_department(),
                        'opportunity_type': self._classify_from_text(item_text),
                        'tags': ['list', 'structured']
                    }
                    
                    # Try to extract deadline
                    deadline = self.extract_deadline(item_text)
                    if deadline:
                        opp['deadline'] = deadline
                    
                    opportunities.append(opp)
                    
        except Exception as e:
            logger.error(f"Error extracting from list: {e}")
        
        return opportunities
    
    def _extract_from_definition_list(self, dl: Tag) -> List[Dict[str, Any]]:
        """Extract opportunities from definition lists."""
        opportunities = []
        
        try:
            terms = dl.select('dt')
            definitions = dl.select('dd')
            
            for i, term in enumerate(terms):
                if i < len(definitions):
                    term_text = term.get_text(strip=True)
                    def_text = definitions[i].get_text(strip=True)
                    
                    # Look for application links in definition
                    app_links = definitions[i].select('a[href]')
                    app_url = ""
                    for link in app_links:
                        href = link.get('href')
                        if href and any(keyword in href.lower() for keyword in ['apply', 'application']):
                            app_url = urljoin(self.url, href)
                            break
                    
                    if app_url or 'deadline' in def_text.lower():
                        opp = {
                            'title': term_text,
                            'description': def_text,
                            'application_url': app_url,
                            'source_url': self.url,
                            'department': self._determine_department(),
                            'opportunity_type': self._classify_from_text(term_text + " " + def_text),
                            'tags': ['definition', 'structured']
                        }
                        
                        # Try to extract deadline
                        deadline = self.extract_deadline(def_text)
                        if deadline:
                            opp['deadline'] = deadline
                        
                        opportunities.append(opp)
                        
        except Exception as e:
            logger.error(f"Error extracting from definition list: {e}")
        
        return opportunities
    
    def _is_valid_opportunity(self, opp: Dict[str, Any]) -> bool:
        """Check if an extracted opportunity is valid and useful."""
        if not opp or not opp.get('title'):
            return False
        
        title = opp.get('title', '').lower()
        description = opp.get('description', '').lower()
        
        # Filter out generic/useless titles
        useless_patterns = [
            'welcome to', 'about us', 'contact us', 'home page',
            'navigation', 'menu', 'footer', 'header', 'sidebar',
            'cookie', 'privacy policy', 'terms of service'
        ]
        
        if any(pattern in title for pattern in useless_patterns):
            return False
        
        # Must have meaningful title (not just dollar amounts)
        if re.match(r'^\$[\d,]+\s*-\s*\$[\d,]+.*$', title.strip()):
            return False  # Skip titles that are just dollar ranges
        
        # Require at least one actionable piece of information
        has_app_url = bool(opp.get('application_url'))
        has_deadline = bool(opp.get('deadline'))
        has_funding = bool(opp.get('funding_amount'))
        has_meaningful_description = len(description) > 50  # Substantial description
        
        # Consider it useful if it has actionable info OR substantial content
        return (has_app_url or has_deadline or has_funding) or has_meaningful_description
    
    def _filter_and_deduplicate_opportunities(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicates and low-quality opportunities."""
        seen_signatures = set()
        filtered_opportunities = []
        
        for opp in opportunities:
            if self._is_valid_opportunity(opp):
                # Create a signature for deduplication
                title = opp.get('title', '').lower().strip()
                app_url = opp.get('application_url', '')
                deadline = str(opp.get('deadline', ''))
                funding = opp.get('funding_amount', '')
                
                # Use multiple fields for deduplication
                signature = f"{title}|{app_url}|{deadline}|{funding}"
                
                if signature not in seen_signatures:
                    seen_signatures.add(signature)
                    filtered_opportunities.append(opp)
                else:
                    # If we have a duplicate, prefer the one with more information
                    existing_idx = None
                    for i, existing_opp in enumerate(filtered_opportunities):
                        existing_signature = f"{existing_opp.get('title', '').lower().strip()}|{existing_opp.get('application_url', '')}|{str(existing_opp.get('deadline', ''))}|{existing_opp.get('funding_amount', '')}"
                        if existing_signature == signature:
                            existing_idx = i
                            break
                    
                    if existing_idx is not None:
                        # Compare and keep the one with more information
                        existing_opp = filtered_opportunities[existing_idx]
                        existing_score = self._score_opportunity(existing_opp)
                        new_score = self._score_opportunity(opp)
                        
                        if new_score > existing_score:
                            filtered_opportunities[existing_idx] = opp
        
        return filtered_opportunities
    
    def _score_opportunity(self, opp: Dict[str, Any]) -> int:
        """Score an opportunity based on how much useful information it has."""
        score = 0
        
        if opp.get('application_url'):
            score += 3  # Application URL is very valuable
        if opp.get('deadline'):
            score += 2  # Deadline is valuable
        if opp.get('funding_amount'):
            score += 2  # Funding info is valuable
        if len(opp.get('description', '')) > 100:
            score += 1  # Detailed description is good
        if len(opp.get('tags', [])) > 3:
            score += 1  # More tags indicate better analysis
        
        return score
    
    def _extract_title_from_block(self, block: Tag) -> str:
        """Extract a meaningful title from a content block."""
        # Try to find headings first
        headings = block.select('h1, h2, h3, h4, h5, h6')
        if headings:
            return headings[0].get_text(strip=True)
        
        # Try strong/bold text
        strong_text = block.select('strong, b')
        if strong_text:
            return strong_text[0].get_text(strip=True)
        
        # Fall back to first sentence
        text = block.get_text(strip=True)
        sentences = text.split('.')
        if sentences:
            return sentences[0].strip()
        
        return ""
    
    def _extract_deadline_text_from_block(self, text: str) -> str:
        """Extract deadline text from a block of text."""
        deadline_patterns = [
            r'deadline[:\s]*([^.]*(?:january|february|march|april|may|june|july|august|september|october|november|december)[^.]*)',
            r'due[:\s]*([^.]*\d{1,2}/\d{1,2}/\d{4}[^.]*)',
            r'apply by[:\s]*([^.]*)',
            r'application deadline[:\s]*([^.]*)',
            r'submissions? due[:\s]*([^.]*)'
        ]
        
        for pattern in deadline_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return ""
    
    def _extract_deadline_from_page(self, soup: BeautifulSoup) -> str:
        """Extract deadline information from a page."""
        text = soup.get_text()
        return self._extract_deadline_text_from_block(text)
    
    def _extract_funding_from_page(self, soup: BeautifulSoup) -> str:
        """Extract funding information from a page."""
        text = soup.get_text()
        
        funding_patterns = [
            r'\$\s?([0-9,]+(?:\.[0-9]{2})?)',
            r'stipend[:\s]*\$?([0-9,]+)',
            r'funding[:\s]*\$?([0-9,]+)',
            r'award[:\s]*\$?([0-9,]+)'
        ]
        
        for pattern in funding_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"${match.group(1)}"
        
        return ""
    
    def _classify_from_text(self, text: str) -> str:
        """Classify opportunity type from text content."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['internship', 'intern']):
            return 'internship'
        elif any(word in text_lower for word in ['funding', 'grant', 'scholarship', 'fellowship']):
            return 'funding'
        else:
            return 'research'
    
    def _determine_department(self) -> str:
        """Determine the department based on URL and configuration."""
        program_name = self.config.get('name', '')
        
        # Map program names to departments
        if 'curis' in self.url.lower() or 'computer science' in program_name.lower():
            return 'Computer Science'
        elif 'bio-x' in self.url.lower() or 'biox' in self.url.lower():
            return 'Bio-X'
        elif 'med.stanford' in self.url:
            return 'Medicine'
        elif 'mse' in self.url or 'materials' in program_name.lower():
            return 'Materials Science'
        elif 'aa.stanford' in self.url or 'aeronautics' in program_name.lower():
            return 'Aeronautics & Astronautics'
        elif 'ee.stanford' in self.url or 'electrical' in program_name.lower():
            return 'Electrical Engineering'
        elif 'biology' in self.url or 'biology' in program_name.lower():
            return 'Biology'
        elif 'epic' in self.url.lower() or 'epic' in program_name.lower():
            return 'Environment & Sustainability'
        elif 'siepr' in self.url or 'economics' in program_name.lower():
            return 'Economics'
        elif 'fsi' in self.url or 'freeman spogli' in program_name.lower():
            return 'International Studies'
        elif 'sgs' in self.url or 'global studies' in program_name.lower():
            return 'Global Studies'
        elif 'healthcare' in self.url or 'healthcare' in program_name.lower():
            return 'Healthcare'
        elif 'humanities' in program_name.lower():
            return 'Humanities'
        else:
            return program_name or 'Stanford Research'
    
    def _extract_opportunity_from_element(self, element: Tag) -> Dict[str, Any]:
        """Extract opportunity data from a specific HTML element."""
        try:
            # Extract title
            title = self._extract_title_from_block(element)
            if not title:
                return {}
            
            # Clean and shorten title
            title = self._clean_title(title)
            
            # Extract description
            description = element.get_text(strip=True)
            
            # Extract application URL
            app_links = element.select('a[href]')
            application_url = ""
            for link in app_links:
                href = link.get('href')
                if href and any(keyword in href.lower() for keyword in ['apply', 'application', 'form']):
                    application_url = urljoin(self.url, href)
                    break
            
            # Extract deadline
            deadline_text = self._extract_deadline_text_from_block(description)
            deadline = self.extract_deadline(deadline_text) if deadline_text else None
            
            # Extract funding
            funding_text = self._extract_funding_from_page(BeautifulSoup(str(element), 'html.parser'))
            funding_amount = self.extract_funding_amount(funding_text) if funding_text else None
            
            # Determine department
            department = self._determine_department()
            
            # Generate tags and classify type
            tags = self.extract_tags(title, description)
            opportunity_type = self.classify_opportunity_type(title, description)
            
            return {
                'title': self.clean_text(title),
                'description': self.clean_text(description[:500]) + "..." if len(description) > 500 else self.clean_text(description),
                'department': department,
                'opportunity_type': opportunity_type,
                'deadline': deadline,
                'funding_amount': funding_amount,
                'application_url': application_url,
                'source_url': self.url,
                'tags': tags
            }
            
        except Exception as e:
            logger.error(f"Error extracting opportunity from element: {e}")
            return {}
    
    def _clean_title(self, title: str) -> str:
        """Clean and improve opportunity titles."""
        if not title:
            return ""
        
        title = title.strip()
        
        # Limit title length
        if len(title) > 100:
            # Try to break at sentence or meaningful point
            if '.' in title[:100]:
                title = title[:title.find('.', 50) + 1]
            elif ',' in title[:100]:
                title = title[:title.find(',', 50)]
            else:
                title = title[:100] + "..."
        
        # Remove redundant text patterns
        cleanup_patterns = [
            r'^Skip to.*?content\s*',
            r'^Navigate to.*?\s*',
            r'\s*Skip to main content\s*',
            r'\s*Stanford University\s*',
        ]
        
        for pattern in cleanup_patterns:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        title = re.sub(r'\s+', ' ', title).strip()
        
        return title
    
    def _extract_prominent_application_links(self, soup: BeautifulSoup, opportunities: List[Dict[str, Any]]) -> None:
        """Look for prominent application links anywhere on the page."""
        try:
            # Look for application links with common patterns
            app_link_patterns = [
                'a[href*="apply"]', 'a[href*="application"]', 'a[href*="form"]',
                'a[href*="submit"]', 'a[href*="register"]', 'a[href*="signup"]',
                '.apply-btn', '.application-btn', '.apply-button', '.application-button',
                '[class*="apply"]', '[class*="application"]'
            ]
            
            for pattern in app_link_patterns:
                links = soup.select(pattern)
                for link in links:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(self.url, href)
                        link_text = link.get_text(strip=True)
                        
                        # Create opportunity from application link
                        if link_text and len(link_text) > 3:  # Meaningful link text
                            opp = {
                                'title': f"{link_text} - {self._determine_department()}",
                                'description': f"Application link found: {link_text}",
                                'application_url': full_url,
                                'source_url': self.url,
                                'department': self._determine_department(),
                                'opportunity_type': self._classify_from_text(link_text),
                                'tags': ['application', 'direct-link']
                            }
                            
                            # Avoid duplicates
                            if not any(existing_opp.get('application_url') == full_url for existing_opp in opportunities):
                                opportunities.append(opp)
                                
        except Exception as e:
            logger.error(f"Error extracting prominent application links: {e}")
    
    def _extract_deadline_text_anywhere(self, soup: BeautifulSoup, opportunities: List[Dict[str, Any]]) -> None:
        """Look for deadline text anywhere on the page and create opportunities."""
        try:
            page_text = soup.get_text()
            
            # Enhanced deadline patterns
            deadline_patterns = [
                # Standard date formats
                r'(?:deadline|due|apply by|submit by)[:\s]*([^.]*(?:january|february|march|april|may|june|july|august|september|october|november|december)[^.]*\d{4})',
                r'(?:deadline|due|apply by)[:\s]*(\d{1,2}/\d{1,2}/\d{4})',
                r'(?:deadline|due|apply by)[:\s]*(\d{1,2}-\d{1,2}-\d{4})',
                # Academic deadlines
                r'applications?\s+due[:\s]*([^.]*(?:january|february|march|april|may|june|july|august|september|october|november|december)[^.]*)',
                r'submission\s+deadline[:\s]*([^.]*)',
                # Specific academic terms
                r'(?:fall|spring|summer|winter)\s+(?:quarter|semester)?\s+deadline[:\s]*([^.]*)',
            ]
            
            for pattern in deadline_patterns:
                matches = re.finditer(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    deadline_text = match.group(1).strip()
                    deadline_date = self.extract_deadline(deadline_text)
                    
                    if deadline_date:
                        # Create opportunity with specific deadline
                        opp = {
                            'title': f"Application Deadline - {self._determine_department()}",
                            'description': f"Research opportunity with deadline: {deadline_text}",
                            'deadline': deadline_date,
                            'source_url': self.url,
                            'department': self._determine_department(),
                            'opportunity_type': 'research',
                            'tags': ['deadline', 'time-sensitive']
                        }
                        
                        # Avoid duplicates
                        if not any(existing_opp.get('deadline') == deadline_date for existing_opp in opportunities):
                            opportunities.append(opp)
                        
        except Exception as e:
            logger.error(f"Error extracting deadline text: {e}") 