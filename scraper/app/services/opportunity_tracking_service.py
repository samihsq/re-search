"""
Opportunity Tracking Service

This service handles similarity detection, duplicate identification, and status tracking
for research opportunities between scrapes.
"""

import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set
from difflib import SequenceMatcher
import re

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc

from loguru import logger

from ..database import SessionLocal
from ..models import Opportunity


class OpportunityTrackingService:
    """Service for tracking opportunity changes and similarity detection."""
    
    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize the tracking service.
        
        Args:
            similarity_threshold: Threshold for considering two opportunities similar (0.0-1.0)
        """
        self.similarity_threshold = similarity_threshold
        
    def _generate_content_hash(self, opportunity: Dict[str, Any]) -> str:
        """Generate a hash of the key content fields for similarity detection."""
        # Combine key fields that identify an opportunity
        key_content = {
            'title': (opportunity.get('title') or '').strip().lower(),
            'description': (opportunity.get('description') or '').strip().lower()[:500],  # First 500 chars
            'department': (opportunity.get('department') or '').strip().lower(),
            'source_url': opportunity.get('source_url', ''),
            'deadline': (opportunity.get('deadline') or '').strip(),
            'funding_amount': (opportunity.get('funding_amount') or '').strip()
        }
        
        # Create a consistent string representation
        content_str = '|'.join([
            key_content['title'],
            key_content['description'],
            key_content['department'],
            key_content['source_url'],
            key_content['deadline'],
            key_content['funding_amount']
        ])
        
        # Generate SHA-256 hash
        return hashlib.sha256(content_str.encode('utf-8')).hexdigest()
    
    def _calculate_similarity(self, opp1: Dict[str, Any], opp2: Dict[str, Any]) -> float:
        """Calculate similarity score between two opportunities."""
        
        def clean_text(text: str) -> str:
            """Clean text for comparison."""
            if not text:
                return ""
            # Remove extra whitespace, convert to lowercase
            text = re.sub(r'\s+', ' ', text.strip().lower())
            return text
        
        # Compare title (highest weight)
        title1 = clean_text(opp1.get('title', ''))
        title2 = clean_text(opp2.get('title', ''))
        title_sim = SequenceMatcher(None, title1, title2).ratio()
        
        # Compare description (medium weight)
        desc1 = clean_text(opp1.get('description', ''))[:200]  # First 200 chars
        desc2 = clean_text(opp2.get('description', ''))[:200]
        desc_sim = SequenceMatcher(None, desc1, desc2).ratio()
        
        # Compare department (medium weight)
        dept1 = clean_text(opp1.get('department', ''))
        dept2 = clean_text(opp2.get('department', ''))
        dept_sim = SequenceMatcher(None, dept1, dept2).ratio() if dept1 and dept2 else 0.5
        
        # Compare source URL (low weight, but important)
        url1 = opp1.get('source_url', '')
        url2 = opp2.get('source_url', '')
        url_sim = 1.0 if url1 == url2 else 0.0
        
        # Weighted similarity score
        # Title is most important (50%), description (30%), department (15%), URL (5%)
        similarity = (
            title_sim * 0.5 +
            desc_sim * 0.3 +
            dept_sim * 0.15 +
            url_sim * 0.05
        )
        
        return similarity
    
    def _find_similar_opportunities(self, new_opp: Dict[str, Any], existing_opportunities: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], float]]:
        """Find similar opportunities from existing ones."""
        similar_opportunities = []
        
        for existing_opp in existing_opportunities:
            similarity = self._calculate_similarity(new_opp, existing_opp)
            if similarity >= self.similarity_threshold:
                similar_opportunities.append((existing_opp, similarity))
        
        # Sort by similarity (highest first)
        similar_opportunities.sort(key=lambda x: x[1], reverse=True)
        return similar_opportunities
    
    def _generate_similarity_group_id(self, opportunity: Dict[str, Any]) -> str:
        """Generate a group ID for similar opportunities."""
        # Use title + department + source domain as group identifier
        title = (opportunity.get('title') or '').strip().lower()
        department = (opportunity.get('department') or '').strip().lower()
        
        # Extract domain from source URL
        source_url = opportunity.get('source_url', '')
        domain = ''
        if source_url:
            from urllib.parse import urlparse
            try:
                domain = urlparse(source_url).netloc.lower()
            except:
                domain = source_url[:50]  # Fallback
        
        group_content = f"{title[:100]}|{department}|{domain}"
        return hashlib.md5(group_content.encode('utf-8')).hexdigest()[:16]
    
    def process_scraped_opportunities(self, opportunities: List[Dict[str, Any]], source_url: str) -> Dict[str, Any]:
        """
        Process scraped opportunities, detect changes, and update tracking status.
        
        Returns:
            Dict with counts of new, updated, and missing opportunities
        """
        if not opportunities:
            return {"new_count": 0, "updated_count": 0, "missing_count": 0, "reappeared_count": 0}
        
        db: Session = SessionLocal()
        current_scrape_time = datetime.now()
        
        try:
            # Get all existing opportunities from the same source
            existing_opps = db.query(Opportunity).filter(
                Opportunity.source_url == source_url
            ).all()
            
            # Convert to dict format for comparison
            existing_opps_dict = [
                {
                    'id': opp.id,
                    'title': opp.title,
                    'description': opp.description,
                    'department': opp.department,
                    'source_url': opp.source_url,
                    'deadline': opp.deadline,
                    'funding_amount': opp.funding_amount,
                    'content_hash': opp.content_hash,
                    'status': opp.status,
                    'consecutive_missing_count': opp.consecutive_missing_count
                }
                for opp in existing_opps
            ]
            
            # Track which existing opportunities were found in this scrape
            found_opportunity_ids = set()
            
            new_count = 0
            updated_count = 0
            reappeared_count = 0
            
            # Process each scraped opportunity
            for scraped_opp in opportunities:
                content_hash = self._generate_content_hash(scraped_opp)
                similarity_group_id = self._generate_similarity_group_id(scraped_opp)
                
                # Try exact hash match first
                exact_match = None
                for existing_opp in existing_opps:
                    if existing_opp.content_hash == content_hash:
                        exact_match = existing_opp
                        break
                
                if exact_match:
                    # Exact match found - update timestamps
                    exact_match.last_seen_at = current_scrape_time
                    exact_match.scraped_at = current_scrape_time
                    
                    # If it was missing, mark as reappeared
                    if exact_match.status == 'missing':
                        exact_match.status = 'active'
                        exact_match.consecutive_missing_count = 0
                        reappeared_count += 1
                        logger.info(f"Opportunity reappeared: {exact_match.title}")
                    
                    found_opportunity_ids.add(exact_match.id)
                    continue
                
                # No exact match - check for similar opportunities
                similar_opps = self._find_similar_opportunities(scraped_opp, existing_opps_dict)
                
                if similar_opps:
                    # Similar opportunity found - update it
                    best_match, similarity_score = similar_opps[0]
                    existing_opp = db.query(Opportunity).filter(Opportunity.id == best_match['id']).first()
                    
                    if existing_opp:
                        # Update content and hash
                        existing_opp.title = scraped_opp.get('title', existing_opp.title)
                        existing_opp.description = scraped_opp.get('description', existing_opp.description)
                        existing_opp.department = scraped_opp.get('department', existing_opp.department)
                        existing_opp.deadline = scraped_opp.get('deadline', existing_opp.deadline)
                        existing_opp.funding_amount = scraped_opp.get('funding_amount', existing_opp.funding_amount)
                        existing_opp.content_hash = content_hash
                        existing_opp.last_seen_at = current_scrape_time
                        existing_opp.last_updated_at = current_scrape_time
                        existing_opp.scraped_at = current_scrape_time
                        
                        # If it was missing, mark as reappeared
                        if existing_opp.status == 'missing':
                            existing_opp.status = 'active'
                            existing_opp.consecutive_missing_count = 0
                            reappeared_count += 1
                            logger.info(f"Similar opportunity reappeared: {existing_opp.title} (similarity: {similarity_score:.2f})")
                        else:
                            existing_opp.status = 'active'
                        
                        found_opportunity_ids.add(existing_opp.id)
                        updated_count += 1
                        logger.info(f"Updated similar opportunity: {existing_opp.title} (similarity: {similarity_score:.2f})")
                        continue
                
                # No match found - create new opportunity
                new_opportunity = Opportunity(
                    title=scraped_opp.get('title', 'Untitled'),
                    description=scraped_opp.get('description', ''),
                    department=scraped_opp.get('department', ''),
                    opportunity_type=scraped_opp.get('opportunity_type', 'research'),
                    eligibility_requirements=scraped_opp.get('eligibility_requirements'),
                    deadline=scraped_opp.get('deadline'),
                    funding_amount=scraped_opp.get('funding_amount'),
                    application_url=scraped_opp.get('application_url', source_url),
                    source_url=source_url,
                    contact_email=scraped_opp.get('contact_email'),
                    tags=scraped_opp.get('tags', []),
                    
                    # LLM metadata
                    llm_parsed=scraped_opp.get('llm_parsed', False),
                    parsing_confidence=scraped_opp.get('parsing_confidence'),
                    scraper_used=scraped_opp.get('scraper_used'),
                    llm_error=scraped_opp.get('llm_error'),
                    processed_at=scraped_opp.get('processed_at'),
                    
                    # Tracking metadata
                    content_hash=content_hash,
                    similarity_group_id=similarity_group_id,
                    first_seen_at=current_scrape_time,
                    last_seen_at=current_scrape_time,
                    last_updated_at=current_scrape_time,
                    status='new',
                    consecutive_missing_count=0,
                    
                    # Standard metadata
                    scraped_at=current_scrape_time,
                    is_active=True
                )
                
                db.add(new_opportunity)
                new_count += 1
                logger.info(f"New opportunity discovered: {new_opportunity.title}")
            
            # Mark opportunities that weren't found in this scrape as missing
            missing_count = 0
            for existing_opp in existing_opps:
                if existing_opp.id not in found_opportunity_ids and existing_opp.status != 'removed':
                    existing_opp.consecutive_missing_count += 1
                    
                    if existing_opp.consecutive_missing_count >= 3:
                        # Missing for 3+ scrapes - mark as removed
                        existing_opp.status = 'removed'
                        existing_opp.is_active = False
                        logger.info(f"Opportunity marked as removed: {existing_opp.title}")
                    else:
                        # Recently missing
                        existing_opp.status = 'missing'
                        missing_count += 1
                        logger.info(f"Opportunity missing (count: {existing_opp.consecutive_missing_count}): {existing_opp.title}")
            
            # After first scrape, change 'new' status to 'active' for opportunities that are still new
            db.query(Opportunity).filter(
                and_(
                    Opportunity.source_url == source_url,
                    Opportunity.status == 'new',
                    Opportunity.first_seen_at < current_scrape_time - timedelta(minutes=1)  # Give 1 minute buffer
                )
            ).update({Opportunity.status: 'active'})
            
            db.commit()
            
            return {
                "new_count": new_count,
                "updated_count": updated_count,
                "missing_count": missing_count,
                "reappeared_count": reappeared_count
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error in opportunity tracking: {e}")
            raise
        finally:
            db.close()
    
    def get_recent_new_opportunities(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get opportunities that are newly discovered in the last N days."""
        db: Session = SessionLocal()
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            new_opportunities = db.query(Opportunity).filter(
                and_(
                    Opportunity.first_seen_at >= cutoff_date,
                    or_(Opportunity.status == 'new', Opportunity.status == 'active'),
                    Opportunity.is_active == True
                )
            ).order_by(desc(Opportunity.first_seen_at)).all()
            
            return [
                {
                    'id': opp.id,
                    'title': opp.title,
                    'description': opp.description,
                    'department': opp.department,
                    'first_seen_at': opp.first_seen_at.isoformat() if opp.first_seen_at else None,
                    'status': opp.status
                }
                for opp in new_opportunities
            ]
            
        finally:
            db.close()


# Global tracking service instance
opportunity_tracking_service = OpportunityTrackingService() 