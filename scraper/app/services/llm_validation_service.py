"""
LLM HTML Parsing Service

This service uses Google Gemini API to parse HTML content from research opportunity pages
and extract structured information in JSON format.
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, date
import random
from pydantic import BaseModel
from bs4 import BeautifulSoup
import re

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from loguru import logger
from ..config import settings


class OpportunityData(BaseModel):
    """Structured data model for parsed research opportunities."""
    title: str
    description: str  # Brief description < 100 words
    tags: List[str] = []
    deadline: Optional[str] = None
    funding_amount: Optional[str] = None
    application_url: Optional[str] = None
    contact_email: Optional[str] = None
    eligibility_requirements: Optional[str] = None
    department: Optional[str] = None
    opportunity_type: Optional[str] = None


class LLMHtmlParsingService:
    """Service for parsing HTML content using Google Gemini API."""
    
    def __init__(self):
        if not GEMINI_AVAILABLE:
            logger.warning("Google GenAI library not available. HTML parsing will be disabled.")
            self.client = None
            return
            
        if not settings.gemini_api_key:
            logger.warning("GEMINI_API_KEY not configured. HTML parsing will be disabled.")
            self.client = None
            return
        
        try:
            self.client = genai.Client(api_key=settings.gemini_api_key)
            logger.info(f"Initialized Gemini client with model: {settings.gemini_model}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            self.client = None
        
        # Track daily API usage to enforce budget limits
        self._calls_today_date: Optional[date] = None
        self._calls_today_count: int = 0

    @property
    def daily_call_count(self) -> int:
        """Get current daily call count."""
        today = date.today()
        if self._calls_today_date != today:
            return 0
        return self._calls_today_count

    @property
    def daily_call_limit(self) -> int:
        """Get daily call limit from settings."""
        return settings.llm_daily_call_limit

    def _check_daily_budget(self) -> bool:
        """Check if we're within daily API call limits."""
        today = date.today()
        
        # Reset counter for new day
        if self._calls_today_date != today:
            self._calls_today_date = today
            self._calls_today_count = 0
        
        # Check if we've exceeded daily limit
        if self._calls_today_count >= settings.llm_daily_call_limit:
            logger.warning(f"Daily Gemini API call limit reached ({settings.llm_daily_call_limit})")
            return False
        
        return True

    def _clean_html_content(self, html_content: str) -> str:
        """Clean and extract text content from HTML."""
        if not html_content:
            return ""
        
        try:
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script, style, and other non-content elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                element.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up whitespace and normalize
            text = re.sub(r'\s+', ' ', text).strip()
            
            # Limit text length to avoid token limits (roughly 6000 characters ≈ 1500 tokens)
            if len(text) > 6000:
                text = text[:6000] + "..."
            
            return text
            
        except Exception as e:
            logger.warning(f"Error cleaning HTML content: {e}")
            return html_content[:6000] if html_content else ""

    def _validate_title_quality(self, opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate that extracted opportunity titles are high quality.
        
        Args:
            opportunities: List of parsed opportunities
            
        Returns:
            Dict with validation results
        """
        if not opportunities:
            return {"valid": True, "issues": []}
        
        issues = []
        for i, opp in enumerate(opportunities):
            title = opp.get('title', '')
            
            # Check for common quality issues
            quality_issues = []
            
            # Check for generic/meaningless titles
            generic_patterns = [
                'application form', 'application deadline', 'apply here', 'research opportunities',
                'undergraduate program', 'graduate program', 'research staff', 'research topics',
                'eligibility', 'deadline', 'apply now'
            ]
            
            if any(pattern in title.lower() for pattern in generic_patterns):
                quality_issues.append(f"Generic title: '{title}'")
            
            # Check for navigation/menu artifacts
            nav_patterns = ['toggle', 'menu', 'navigation', 'programtoggle', 'overview']
            if any(pattern in title.lower() for pattern in nav_patterns):
                quality_issues.append(f"Navigation artifact: '{title}'")
            
            # Check for overly long titles (likely concatenated text)
            if len(title.split()) > 12:
                quality_issues.append(f"Overly long title: '{title}'")
            
            # Check for empty or very short titles
            if len(title.strip()) < 3:
                quality_issues.append(f"Too short title: '{title}'")
            
            # Check for titles that are just department names
            dept_only_patterns = ['department', 'school of', 'institute', 'center for']
            if any(pattern in title.lower() for pattern in dept_only_patterns) and len(title.split()) <= 3:
                quality_issues.append(f"Department-only title: '{title}'")
            
            if quality_issues:
                issues.append({
                    "opportunity_index": i,
                    "title": title,
                    "issues": quality_issues
                })
        
        # Consider results invalid if more than 30% have quality issues
        threshold = len(opportunities) * 0.3
        is_valid = len(issues) <= threshold
        
        return {
            "valid": is_valid,
            "issues": issues,
            "total_opportunities": len(opportunities),
            "problematic_count": len(issues),
            "quality_score": (len(opportunities) - len(issues)) / len(opportunities) if opportunities else 1.0
        }

    async def _call_gemini_api(self, cleaned_html: str, source_url: str) -> Dict[str, Any]:
        """Make API call to Gemini for HTML parsing."""
        if not self.client:
            return {"error": "Gemini client not available"}
        
        if not self._check_daily_budget():
            return {"error": "daily_budget_exceeded"}
        
        try:
            # Create the parsing prompt with strong JSON enforcement
            prompt = f"""
You are an expert at parsing research opportunity web pages. Your job is to extract clean, high-quality information about research programs and opportunities.

CRITICAL REQUIREMENTS:
1. TITLE must be the actual name of the research program, lab, or organization - NOT a concatenated mess of text
2. DESCRIPTION must be a clear, concise summary (1-3 sentences) of what the program offers - NOT raw HTML text
3. Only extract genuine research opportunities, programs, or labs - ignore navigation menus, headers, footers

IMPORTANT: You MUST respond with ONLY a valid JSON array. Start with [ and end with ].

Source URL: {source_url}

HTML Content:
{cleaned_html}

For each legitimate research opportunity or program, extract:

- title: The clean, proper name of the research program, lab, or organization (e.g. "Stanford Bio-X USRP", "Machine Learning Lab", "Aeronautics Research Program")
- description: A clear 1-3 sentence summary of what the program offers (e.g. "10-week summer research program for undergraduates in interdisciplinary biological sciences with full stipend support.")
- tags: Relevant keywords (e.g. ["Summer Research", "Biology", "Undergraduate"])
- deadline: Application deadline if clearly mentioned
- funding_amount: Specific funding/stipend amounts if mentioned (e.g. "$6000 stipend", "Paid position")
- application_url: Direct application link if different from source URL
- contact_email: Contact email if provided
- eligibility_requirements: Who can apply (e.g. "Undergraduate students", "PhD candidates")
- department: The academic department (e.g. "Computer Science", "Biology")
- opportunity_type: MUST be one of: "research", "internship", "funding", "fellowship", "leadership"

QUALITY STANDARDS:
- Titles should be 3-8 words, not full sentences
- Descriptions should be informative summaries, not raw text dumps
- Only include real opportunities, not general information pages
- If no clear opportunities exist, return empty array: []

Example GOOD output:
[
  {{
    "title": "Stanford Bio-X USRP",
    "description": "10-week summer research program for undergraduates in interdisciplinary biological sciences with full stipend support.",
    "tags": ["Summer Research", "Biology", "Interdisciplinary", "Undergraduate"],
    "deadline": "February 1, 2025",
    "funding_amount": "$6000 stipend",
    "application_url": null,
    "contact_email": "biox-usrp@stanford.edu",
    "eligibility_requirements": "Stanford undergraduate students",
    "department": "Bio-X",
    "opportunity_type": "research"
  }}
]

Respond with ONLY the JSON array:
"""

            # Make the API call WITHOUT response_mime_type for gemma-3-27b-it
            response = self.client.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=settings.llm_max_tokens,
                    temperature=0.1  # Low temperature for consistent extraction
                    # Note: No response_mime_type since gemma-3-27b-it doesn't support JSON mode
                )
            )
            
            # Increment API call counter
            self._calls_today_count += 1
            
            # Clean and parse the response
            try:
                response_text = response.text.strip()
                
                # Remove any markdown formatting if present
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.startswith("```"):
                    response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                
                # Clean up any extra text before/after JSON
                response_text = response_text.strip()
                
                # Find JSON array boundaries
                start_idx = response_text.find('[')
                end_idx = response_text.rfind(']')
                
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    json_text = response_text[start_idx:end_idx + 1]
                else:
                    json_text = response_text
                
                # Additional cleaning for gemma-3-27b-it issues
                # Fix common issues with truncated or malformed JSON
                if json_text.endswith('"...') or json_text.endswith('"cont...'):
                    # Handle truncated responses - remove incomplete last entry
                    lines = json_text.split('\n')
                    # Find the last complete object by looking for proper closing
                    for i in range(len(lines) - 1, -1, -1):
                        if lines[i].strip().endswith('}') or lines[i].strip().endswith('},'):
                            # Reconstruct JSON up to this point
                            json_text = '\n'.join(lines[:i+1])
                            # Ensure proper array closing
                            if not json_text.rstrip().endswith(']'):
                                # Remove trailing comma if present
                                json_text = json_text.rstrip().rstrip(',')
                                json_text += '\n]'
                            break
                
                # Fix common escape sequence issues
                json_text = json_text.replace('\\"', '"')  # Fix over-escaped quotes
                json_text = json_text.replace('\\n', ' ')  # Replace newlines with spaces
                
                parsed_opportunities = json.loads(json_text)
                if not isinstance(parsed_opportunities, list):
                    parsed_opportunities = []
                
                # Validate title quality
                quality_validation = self._validate_title_quality(parsed_opportunities)
                    
                logger.info(f"Successfully parsed {len(parsed_opportunities)} opportunities from {source_url}")
                return {
                    "success": True,
                    "opportunities": parsed_opportunities,
                    "source_url": source_url,
                    "quality_validation": quality_validation
                }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response from Gemini: {e}")
                logger.debug(f"Raw response: {response.text[:500]}...")
                return {"error": f"json_decode_error: {e}"}
                
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            return {"error": f"api_call_failed: {e}"}

    async def parse_html_content(self, html_content: str, source_url: str) -> Dict[str, Any]:
        """
        Parse HTML content to extract research opportunities with retry logic for invalid JSON.
        
        Args:
            html_content: Raw HTML content from the scraped page
            source_url: URL of the source page
            
        Returns:
            Dict containing parsed opportunities or error information
        """
        if not settings.enable_llm_parsing:
            logger.info("LLM parsing is disabled")
            return {"error": "llm_parsing_disabled"}
        
        if not self.client:
            logger.warning("Gemini client not available")
            return {"error": "gemini_not_available"}
        
        # Sample based on percentage setting
        if random.random() > settings.llm_parse_percent:
            logger.info(f"Skipping LLM parsing (sampling: {settings.llm_parse_percent})")
            return {"error": "skipped_sampling"}
        
        # Clean the HTML content
        cleaned_html = self._clean_html_content(html_content)
        if not cleaned_html:
            logger.warning("No content to parse after HTML cleaning")
            return {"error": "no_content_after_cleaning"}
        
        # Make API call with retries for invalid JSON and poor quality titles
        max_json_retries = 3  # Extra retries specifically for JSON parsing issues
        max_quality_retries = 5  # Retries for poor title quality
        
        for attempt in range(settings.max_parsing_retries + 1):
            try:
                result = await asyncio.wait_for(
                    self._call_gemini_api(cleaned_html, source_url),
                    timeout=settings.parsing_timeout
                )
                
                # If successful, check title quality
                if result.get("success"):
                    quality_validation = result.get("quality_validation", {})
                    
                    # If quality is good or we've exhausted quality retries, return
                    if quality_validation.get("valid", True) or attempt >= max_quality_retries:
                        if not quality_validation.get("valid", True):
                            logger.warning(f"Accepting low-quality titles after {max_quality_retries} retries for {source_url}")
                            logger.warning(f"Quality issues: {quality_validation.get('issues', [])}")
                        return result
                    else:
                        # Poor quality titles - retry with enhanced prompt
                        quality_score = quality_validation.get("quality_score", 0)
                        problematic_count = quality_validation.get("problematic_count", 0)
                        logger.warning(f"Poor title quality (score: {quality_score:.2f}, {problematic_count} issues) for {source_url} - retry {attempt + 1}/{max_quality_retries}")
                        await asyncio.sleep(1.0 * (attempt + 1))  # Short delay for quality retries
                        continue
                
                # If it's a JSON decode error and we have retries left, try again
                error_msg = result.get("error", "")
                if "json_decode_error" in error_msg and attempt < max_json_retries:
                    logger.warning(f"JSON parsing attempt {attempt + 1} failed: {error_msg}. Retrying...")
                    await asyncio.sleep(1.0 * (attempt + 1))  # Exponential backoff
                    continue
                
                # For other errors, use normal retry logic
                if attempt < settings.max_parsing_retries:
                    logger.warning(f"Parsing attempt {attempt + 1} failed: {error_msg}. Retrying...")
                    await asyncio.sleep(2.0 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    return result
                    
            except asyncio.TimeoutError:
                error_msg = f"LLM parsing timeout after {settings.parsing_timeout}s"
                if attempt < settings.max_parsing_retries:
                    logger.warning(f"{error_msg}. Retrying...")
                    await asyncio.sleep(2.0 * (attempt + 1))
                    continue
                else:
                    logger.error(error_msg)
                    return {"error": "parsing_timeout"}
            except Exception as e:
                error_msg = f"Unexpected error during LLM parsing: {e}"
                if attempt < settings.max_parsing_retries:
                    logger.warning(f"{error_msg}. Retrying...")
                    await asyncio.sleep(2.0 * (attempt + 1))
                    continue
                else:
                    logger.error(error_msg)
                    return {"error": f"unexpected_error: {e}"}
        
        return {"error": "max_retries_exceeded"}

    async def process_opportunities_batch(
        self, 
        html_contents: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Process a batch of HTML contents for opportunities.
        
        Args:
            html_contents: List of dicts with 'html' and 'source_url' keys
            
        Returns:
            Dict with parsing results and statistics
        """
        if not html_contents:
            return {
                "total_processed": 0,
                "successful_parses": 0,
                "failed_parses": 0,
                "opportunities_found": 0,
                "results": []
            }
        
        logger.info(f"Processing batch of {len(html_contents)} HTML contents")
        
        results = []
        successful_parses = 0
        opportunities_found = 0
        
        for item in html_contents:
            html_content = item.get('html', '')
            source_url = item.get('source_url', 'unknown')
            
            try:
                parse_result = await self.parse_html_content(html_content, source_url)
                
                if parse_result.get("success"):
                    successful_parses += 1
                    opportunities = parse_result.get("opportunities", [])
                    opportunities_found += len(opportunities)
                
                results.append({
                    "source_url": source_url,
                    "parse_result": parse_result
                })
                
            except Exception as e:
                logger.error(f"Error processing {source_url}: {e}")
                results.append({
                    "source_url": source_url,
                    "parse_result": {"error": f"processing_error: {e}"}
                })
        
        return {
            "total_processed": len(html_contents),
            "successful_parses": successful_parses,
            "failed_parses": len(html_contents) - successful_parses,
            "opportunities_found": opportunities_found,
            "results": results,
            "api_calls_used": self._calls_today_count
        }


# Global service instance
llm_parsing_service = LLMHtmlParsingService() 