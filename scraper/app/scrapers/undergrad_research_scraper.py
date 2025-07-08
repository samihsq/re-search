from typing import List, Dict, Any
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin

from .base_scraper import BaseScraper
from loguru import logger


class UndergradResearchScraper(BaseScraper):
    """Scraper for Stanford Undergraduate Research funding opportunities."""
    
    def extract_opportunities(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract funding opportunities from the undergraduate research page."""
        opportunities = []
        
        try:
            # Look for different possible opportunity containers
            opportunity_selectors = [
                '.funding-opportunity',
                '.opportunity',
                '.grant-item',
                '.funding-item',
                'section[class*="funding"]',
                'div[class*="opportunity"]',
                'article',
                '.content-block'
            ]
            
            opportunity_elements = []
            for selector in opportunity_selectors:
                elements = soup.select(selector)
                if elements:
                    opportunity_elements = elements
                    logger.info(f"Found {len(elements)} opportunities using selector: {selector}")
                    break
            
            # If no specific containers found, look for structured content
            if not opportunity_elements:
                # Look for headers that might indicate funding opportunities
                headers = soup.find_all(['h2', 'h3', 'h4'], string=lambda text: text and any(
                    keyword in text.lower() for keyword in 
                    ['funding', 'grant', 'award', 'opportunity', 'program']
                ))
                
                for header in headers:
                    # Extract content around each header
                    content_element = header.parent or header
                    opportunity_elements.append(content_element)
                
                logger.info(f"Found {len(opportunity_elements)} opportunities from headers")
            
            # Extract data from each opportunity element
            for element in opportunity_elements:
                opportunity = self._extract_opportunity_from_element(element)
                if opportunity and opportunity.get('title'):
                    opportunities.append(opportunity)
            
            # If still no opportunities, try generic content extraction
            if not opportunities:
                opportunities = self._extract_generic_opportunities(soup)
            
        except Exception as e:
            logger.error(f"Error extracting opportunities: {e}")
        
        logger.info(f"Extracted {len(opportunities)} opportunities from undergraduate research page")
        return opportunities
    
    def _extract_opportunity_from_element(self, element: Tag) -> Dict[str, Any]:
        """Extract opportunity data from a single HTML element."""
        try:
            # Extract title
            title = self._extract_title(element)
            if not title:
                return {}
            
            # Extract description
            description = self._extract_description(element)
            
            # Extract other fields
            deadline_text = self._extract_deadline_text(element)
            deadline = self.extract_deadline(deadline_text) if deadline_text else None
            
            funding_amount = self._extract_funding_amount_text(element)
            funding_amount = self.extract_funding_amount(funding_amount) if funding_amount else None
            
            eligibility = self._extract_eligibility(element)
            contact_email = self._extract_contact_email(element)
            application_url = self._extract_application_url(element)
            department = self._extract_department(element)
            
            # Generate tags and classify type
            tags = self.extract_tags(title, description)
            opportunity_type = self.classify_opportunity_type(title, description)
            
            return {
                'title': self.clean_text(title),
                'description': self.clean_text(description),
                'department': self.standardize_department(department),
                'opportunity_type': opportunity_type,
                'eligibility_requirements': self.clean_text(eligibility),
                'deadline': deadline,
                'funding_amount': funding_amount,
                'application_url': application_url,
                'source_url': self.url,
                'contact_email': contact_email,
                'tags': tags
            }
            
        except Exception as e:
            logger.error(f"Error extracting opportunity from element: {e}")
            return {}
    
    def _extract_title(self, element: Tag) -> str:
        """Extract title from element."""
        # Try different title selectors
        title_selectors = ['h1', 'h2', 'h3', 'h4', '.title', '.heading', '.name']
        
        for selector in title_selectors:
            title_elem = element.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title and len(title) > 3:  # Minimum title length
                    return title
        
        # Fallback: use element text if it's short enough to be a title
        element_text = element.get_text(strip=True)
        if element_text and len(element_text) < 200:
            return element_text.split('\n')[0]  # Take first line
        
        return ""
    
    def _extract_description(self, element: Tag) -> str:
        """Extract description from element."""
        # Try different description selectors
        desc_selectors = [
            '.description', '.content', '.details', '.summary',
            'p', '.text', '.info'
        ]
        
        descriptions = []
        for selector in desc_selectors:
            desc_elements = element.select(selector)
            for desc_elem in desc_elements:
                desc_text = desc_elem.get_text(strip=True)
                if desc_text and len(desc_text) > 20:  # Minimum description length
                    descriptions.append(desc_text)
        
        if descriptions:
            return ' '.join(descriptions[:3])  # Limit to first 3 paragraphs
        
        # Fallback: use all text content
        all_text = element.get_text(strip=True)
        if len(all_text) > 200:
            return all_text[:1000]  # Limit length
        
        return ""
    
    def _extract_deadline_text(self, element: Tag) -> str:
        """Extract deadline-related text from element."""
        deadline_selectors = [
            '.deadline', '.due-date', '.apply-by', '[class*="deadline"]',
            '[class*="due"]', '.date'
        ]
        
        for selector in deadline_selectors:
            deadline_elem = element.select_one(selector)
            if deadline_elem:
                return deadline_elem.get_text(strip=True)
        
        # Look for deadline in text content
        text = element.get_text()
        deadline_keywords = ['deadline', 'due date', 'apply by', 'submission deadline']
        
        for keyword in deadline_keywords:
            if keyword in text.lower():
                # Extract sentence containing the keyword
                sentences = text.split('.')
                for sentence in sentences:
                    if keyword in sentence.lower():
                        return sentence.strip()
        
        return ""
    
    def _extract_funding_amount_text(self, element: Tag) -> str:
        """Extract funding amount text from element."""
        amount_selectors = [
            '.amount', '.funding', '.award', '.stipend',
            '[class*="amount"]', '[class*="funding"]'
        ]
        
        for selector in amount_selectors:
            amount_elem = element.select_one(selector)
            if amount_elem:
                return amount_elem.get_text(strip=True)
        
        # Look for dollar amounts in text
        text = element.get_text()
        if '$' in text:
            sentences = text.split('.')
            for sentence in sentences:
                if '$' in sentence:
                    return sentence.strip()
        
        return ""
    
    def _extract_eligibility(self, element: Tag) -> str:
        """Extract eligibility requirements from element."""
        eligibility_selectors = [
            '.eligibility', '.requirements', '.criteria',
            '[class*="eligibility"]', '[class*="requirement"]'
        ]
        
        for selector in eligibility_selectors:
            eligibility_elem = element.select_one(selector)
            if eligibility_elem:
                return eligibility_elem.get_text(strip=True)
        
        # Look for eligibility keywords in text
        text = element.get_text()
        eligibility_keywords = ['eligible', 'requirements', 'criteria', 'must be']
        
        for keyword in eligibility_keywords:
            if keyword in text.lower():
                sentences = text.split('.')
                for sentence in sentences:
                    if keyword in sentence.lower():
                        return sentence.strip()
        
        return ""
    
    def _extract_contact_email(self, element: Tag) -> str:
        """Extract contact email from element."""
        # Look for email links
        email_links = element.select('a[href^="mailto:"]')
        if email_links:
            return email_links[0]['href'].replace('mailto:', '')
        
        # Look for email addresses in text
        import re
        text = element.get_text()
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        if emails:
            return emails[0]
        
        return ""
    
    def _extract_application_url(self, element: Tag) -> str:
        """Extract application URL from element."""
        # Look for application links
        app_selectors = [
            'a[href*="apply"]', 'a[href*="application"]',
            '.apply-link', '.application-link', '[class*="apply"]'
        ]
        
        for selector in app_selectors:
            link = element.select_one(selector)
            if link and link.get('href'):
                url = link['href']
                if url.startswith('http'):
                    return url
                else:
                    return urljoin(self.url, url)
        
        return ""
    
    def _extract_department(self, element: Tag) -> str:
        """Extract department information from element."""
        dept_selectors = [
            '.department', '.dept', '.school', '.division',
            '[class*="department"]', '[class*="dept"]'
        ]
        
        for selector in dept_selectors:
            dept_elem = element.select_one(selector)
            if dept_elem:
                return dept_elem.get_text(strip=True)
        
        # Default to undergraduate research if not specified
        return "Undergraduate Research"
    
    def _extract_generic_opportunities(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract opportunities using generic content analysis."""
        opportunities = []
        
        try:
            # Look for any text that might be opportunities
            all_text = soup.get_text()
            
            # Split by common delimiters and look for opportunity-like content
            sections = []
            for delimiter in ['\n\n', '***', '---', '===']:
                if delimiter in all_text:
                    sections = all_text.split(delimiter)
                    break
            
            if not sections:
                # Fallback: split by paragraphs
                paragraphs = soup.find_all('p')
                sections = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50]
            
            for section in sections:
                if len(section) > 100 and any(keyword in section.lower() for keyword in 
                    ['fund', 'grant', 'award', 'opportunity', 'program', 'fellowship']):
                    
                    # Try to extract a title (first line or sentence)
                    lines = section.strip().split('\n')
                    title = lines[0] if lines else section[:100]
                    
                    opportunity = {
                        'title': self.clean_text(title),
                        'description': self.clean_text(section),
                        'department': 'Undergraduate Research',
                        'opportunity_type': self.classify_opportunity_type(title, section),
                        'source_url': self.url,
                        'tags': self.extract_tags(title, section)
                    }
                    
                    opportunities.append(opportunity)
            
        except Exception as e:
            logger.error(f"Error in generic opportunity extraction: {e}")
        
        return opportunities[:10]  # Limit to avoid too many low-quality results 