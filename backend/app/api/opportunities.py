from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc, text
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta

from ..database import get_db
from ..models import Opportunity as OpportunityModel, ScrapingLog
from ..schemas import (
    Opportunity, OpportunityCreate, OpportunityUpdate, 
    SearchRequest, SearchResponse, SearchFilters,
    OpportunityStats, ScrapingRequest, ScrapingResponse,
    PaginationParams
)
from ..services.scraping_service import scraping_service
from ..services.llm_validation_service import llm_parsing_service
from loguru import logger
from ..config import settings

router = APIRouter()


@router.get("/")
async def get_opportunities(
    skip: int = Query(0, ge=0, description="Number of opportunities to skip"),
    limit: int = Query(20, ge=1, le=10000, description="Number of opportunities to return (increased limit)"),
    department: Optional[str] = Query(None, description="Filter by department"),
    opportunity_type: Optional[str] = Query(None, description="Filter by opportunity type"),
    is_active: bool = Query(True, description="Filter by active status"),
    deadline_from: Optional[str] = Query(None, description="Filter by deadline text (NOTE: now text-based, not date filtering)"),
    deadline_to: Optional[str] = Query(None, description="Filter by deadline text (NOTE: now text-based, not date filtering)"),
    has_funding: Optional[bool] = Query(None, description="Filter opportunities with funding information"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    sort_by: str = Query("scraped_at", description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db)
):
    """Get opportunities with filtering and pagination (enhanced limits)."""
    
    query = db.query(OpportunityModel)
    
    # Apply filters
    if is_active is not None:
        query = query.filter(OpportunityModel.is_active == is_active)
    
    if department:
        query = query.filter(OpportunityModel.department.ilike(f"%{department}%"))
    
    if opportunity_type:
        query = query.filter(OpportunityModel.opportunity_type == opportunity_type)
    
    if has_funding is not None:
        if has_funding:
            query = query.filter(OpportunityModel.funding_amount.isnot(None))
        else:
            query = query.filter(OpportunityModel.funding_amount.is_(None))
    
    if search:
        search_filter = or_(
            OpportunityModel.title.ilike(f"%{search}%"),
            OpportunityModel.description.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    # Apply sorting
    if hasattr(OpportunityModel, sort_by):
        sort_column = getattr(OpportunityModel, sort_by)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
    
    # Apply pagination
    opportunities = query.offset(skip).limit(limit).all()
    
    return opportunities


@router.get("/count")
async def get_opportunities_count(db: Session = Depends(get_db)):
    """Return total count of active opportunities (for pagination)."""
    total = db.query(OpportunityModel).filter(OpportunityModel.is_active == True).count()
    return {"total": total}


# =============================================================================
# DATABASE MANAGEMENT ENDPOINTS (must come before /{opportunity_id} routes)
# =============================================================================

@router.delete("/admin/delete-all")
async def delete_all_opportunities(
    confirm: str = Query(..., description="Type 'DELETE_ALL' to confirm"),
    db: Session = Depends(get_db)
):
    """Delete ALL opportunities from the database (DESTRUCTIVE OPERATION)."""
    
    if confirm != "DELETE_ALL":
        raise HTTPException(
            status_code=400, 
            detail="Must provide confirm='DELETE_ALL' to delete all opportunities"
        )
    
    try:
        # Get count before deletion
        total_count = db.query(OpportunityModel).count()
        
        # Delete all opportunities
        deleted_count = db.query(OpportunityModel).delete()
        db.commit()
        
        logger.warning(f"DELETED ALL {deleted_count} opportunities from database")
        return {
            "message": f"Successfully deleted ALL {deleted_count} opportunities",
            "previous_total": total_count,
            "deleted_count": deleted_count
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete all opportunities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete opportunities: {e}")


@router.delete("/admin/delete-inactive")
async def delete_inactive_opportunities(db: Session = Depends(get_db)):
    """Delete all inactive opportunities."""
    try:
        deleted_count = db.query(OpportunityModel).filter(
            OpportunityModel.is_active == False
        ).delete()
        db.commit()
        
        logger.info(f"Deleted {deleted_count} inactive opportunities")
        return {"message": f"Deleted {deleted_count} inactive opportunities"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete inactive opportunities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete inactive opportunities: {e}")


@router.post("/admin/bulk-deactivate")
async def bulk_deactivate_opportunities(
    opportunity_ids: List[int],
    db: Session = Depends(get_db)
):
    """Bulk deactivate multiple opportunities."""
    try:
        updated_count = db.query(OpportunityModel).filter(
            OpportunityModel.id.in_(opportunity_ids)
        ).update({"is_active": False}, synchronize_session=False)
        db.commit()
        
        logger.info(f"Deactivated {updated_count} opportunities")
        return {"message": f"Deactivated {updated_count} opportunities"}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to bulk deactivate opportunities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/reset-database")
async def reset_database(
    confirm: str = Query(..., description="Type 'RESET_DATABASE' to confirm"),
    db: Session = Depends(get_db)
):
    """Reset database by deleting all opportunities and related data."""
    
    if confirm != "RESET_DATABASE":
        raise HTTPException(
            status_code=400,
            detail="Must provide confirm='RESET_DATABASE' to reset database"
        )
    
    try:
        # Delete all notifications first (foreign key constraint)
        db.execute(text("DELETE FROM notifications_sent"))
        
        # Delete all opportunities
        deleted_opps = db.query(OpportunityModel).delete()
        
        # Delete scraping logs if they exist
        try:
            db.execute(text("DELETE FROM scraping_logs"))
        except:
            pass  # Table might not exist
        
        # Delete search queries if they exist
        try:
            db.execute(text("DELETE FROM search_queries"))
        except:
            pass  # Table might not exist
        
        db.commit()
        
        logger.warning(f"DATABASE RESET: Deleted {deleted_opps} opportunities and all related data")
        return {
            "message": "Database reset completed",
            "opportunities_deleted": deleted_opps,
            "status": "success"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to reset database: {e}")
        raise HTTPException(status_code=500, detail=f"Database reset failed: {e}")


# =============================================================================
# ENHANCED SEARCH WITH LLM/RAG CAPABILITIES
# =============================================================================

@router.post("/search", response_model=SearchResponse)
async def search_opportunities(
    search_request: SearchRequest,
    db: Session = Depends(get_db)
):
    """Advanced search for opportunities with filters and optional LLM enhancement."""
    
    query = db.query(OpportunityModel).filter(OpportunityModel.is_active == True)
    
    # Apply text search
    if search_request.query:
        search_terms = search_request.query.lower().split()
        search_conditions = []
        
        for term in search_terms:
            term_condition = or_(
                OpportunityModel.title.ilike(f"%{term}%"),
                OpportunityModel.description.ilike(f"%{term}%"),
                OpportunityModel.department.ilike(f"%{term}%"),
                OpportunityModel.eligibility_requirements.ilike(f"%{term}%")
            )
            search_conditions.append(term_condition)
        
        # All terms must match (AND logic)
        if search_conditions:
            query = query.filter(and_(*search_conditions))
    
    # Apply filters
    if search_request.filters:
        filters = search_request.filters
        
        if filters.departments:
            dept_conditions = [
                OpportunityModel.department.ilike(f"%{dept}%") 
                for dept in filters.departments
            ]
            query = query.filter(or_(*dept_conditions))
        
        if filters.opportunity_types:
            query = query.filter(
                OpportunityModel.opportunity_type.in_(filters.opportunity_types)
            )
        
        if filters.deadline_from:
            query = query.filter(OpportunityModel.deadline >= filters.deadline_from)
        
        if filters.deadline_to:
            query = query.filter(OpportunityModel.deadline <= filters.deadline_to)
        
        if filters.has_funding is not None:
            if filters.has_funding:
                query = query.filter(OpportunityModel.funding_amount.isnot(None))
            else:
                query = query.filter(OpportunityModel.funding_amount.is_(None))
        
        if filters.keywords:
            keyword_conditions = []
            for keyword in filters.keywords:
                keyword_condition = or_(
                    OpportunityModel.title.ilike(f"%{keyword}%"),
                    OpportunityModel.description.ilike(f"%{keyword}%")
                )
                keyword_conditions.append(keyword_condition)
            
            if keyword_conditions:
                query = query.filter(or_(*keyword_conditions))
    
    # Get total count before pagination
    total_count = query.count()
    
    # Apply sorting
    if hasattr(OpportunityModel, search_request.sort_by):
        sort_column = getattr(OpportunityModel, search_request.sort_by)
        if search_request.sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
    
    # Apply pagination
    opportunities = query.offset(search_request.offset).limit(search_request.limit).all()
    
    # Calculate pagination info
    page = (search_request.offset // search_request.limit) + 1
    page_size = search_request.limit
    has_next = (search_request.offset + search_request.limit) < total_count
    has_previous = search_request.offset > 0
    
    return SearchResponse(
        opportunities=opportunities,
        total_count=total_count,
        page=page,
        page_size=page_size,
        has_next=has_next,
        has_previous=has_previous,
        query_info={
            "search_query": search_request.query,
            "filters_applied": search_request.filters.dict() if search_request.filters else None,
            "total_results": total_count
        }
    )


@router.post("/search/llm")
async def llm_enhanced_search(
    query: str = Query(..., description="Natural language query"),
    limit: int = Query(50, ge=1, le=1000, description="Number of results to return"),
    use_vector_search: bool = Query(False, description="Use vector similarity search if available"),
    db: Session = Depends(get_db)
):
    """LLM-powered natural language search over opportunities (RAG-style)."""
    
    import time
    start_time = time.time()
    
    if not llm_parsing_service.client:
        raise HTTPException(
            status_code=503,
            detail="LLM service not available. Check GEMINI_API_KEY configuration."
        )
    
    try:
        # Get all active opportunities for LLM processing
        all_opportunities = db.query(OpportunityModel).filter(
            OpportunityModel.is_active == True
        ).all()
        
        if not all_opportunities:
            return {
                "query": query,
                "results": [],
                "total_found": 0,
                "search_method": "llm_enhanced",
                "ai_explanation": "No opportunities found in database",
                "processing_time": time.time() - start_time
            }
        
        # Prepare content for LLM analysis
        content_for_analysis = []
        for opp in all_opportunities:
            opp_text = f"""
Title: {opp.title}
Description: {opp.description or 'No description'}
Department: {opp.department or 'Not specified'}
Type: {opp.opportunity_type}
Eligibility: {opp.eligibility_requirements or 'Not specified'}
Deadline: {opp.deadline or 'Not specified'}
Funding: {opp.funding_amount or 'Not specified'}
Tags: {', '.join(opp.tags) if opp.tags else 'None'}
""".strip()
            content_for_analysis.append({
                "id": opp.id,
                "content": opp_text,
                "opportunity": opp
            })
        
        # Use LLM to analyze and rank opportunities based on the query
        llm_prompt = f"""
You are a research opportunity matching expert. Analyze the following research opportunities and rank them by relevance to this query: "{query}"

Return ONLY a JSON array of opportunity IDs ranked by relevance (most relevant first). Include only the IDs that are actually relevant (minimum 50% relevance). Format: [id1, id2, id3, ...]

Opportunities to analyze:
{chr(10).join([f"ID {item['id']}: {item['content']}" for item in content_for_analysis[:20]])}
"""
        
        # Call LLM for ranking
        try:
            from google.genai import types
            response = llm_parsing_service.client.models.generate_content(
                model=settings.gemini_model,
                contents=llm_prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=1000,
                    temperature=0.3
                )
            )
            
            # Parse LLM response to get ranked IDs
            response_text = response.text.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("\n", 1)[1].rsplit("\n", 1)[0]
            
            import json
            ranked_ids = json.loads(response_text)
            
            # Get opportunities in LLM-ranked order
            ranked_opportunities = []
            opp_dict = {opp.id: opp for opp in all_opportunities}
            
            for opp_id in ranked_ids[:limit]:
                if opp_id in opp_dict:
                    ranked_opportunities.append(opp_dict[opp_id])
            
            # Generate AI explanation/summary of the selected opportunities
            ai_explanation = "AI analysis completed successfully."
            if ranked_opportunities:
                explanation_prompt = f"""
You are a research advisor. The user searched for: "{query}"

I found {len(ranked_opportunities)} relevant research opportunities. Please provide a helpful 2-3 sentence summary explaining why these opportunities match the user's search and what makes them relevant.

Selected opportunities:
{chr(10).join([f"- {opp.title}: {opp.description or 'No description'}" for opp in ranked_opportunities[:5]])}

Provide a conversational, helpful explanation that guides the user about what they found.
"""
                
                try:
                    explanation_response = llm_parsing_service.client.models.generate_content(
                        model=settings.gemini_model,
                        contents=explanation_prompt,
                        config=types.GenerateContentConfig(
                            max_output_tokens=500,
                            temperature=0.7
                        )
                    )
                    ai_explanation = explanation_response.text.strip()
                except Exception as e:
                    logger.warning(f"Failed to generate AI explanation: {e}")
                    ai_explanation = f"Found {len(ranked_opportunities)} relevant opportunities matching your search for '{query}'."
            
            logger.info(f"LLM search for '{query}' returned {len(ranked_opportunities)} ranked results")
            
            return {
                "query": query,
                "results": ranked_opportunities,
                "total_found": len(ranked_opportunities),
                "search_method": "llm_enhanced",
                "llm_ranking": True,
                "total_analyzed": len(all_opportunities),
                "ai_explanation": ai_explanation,
                "processing_time": time.time() - start_time
            }
            
        except Exception as llm_error:
            logger.error(f"LLM ranking failed: {llm_error}")
            # Fallback to traditional search
            fallback_results = db.query(OpportunityModel).filter(
                and_(
                    OpportunityModel.is_active == True,
                    or_(
                        OpportunityModel.title.ilike(f"%{query}%"),
                        OpportunityModel.description.ilike(f"%{query}%"),
                        OpportunityModel.department.ilike(f"%{query}%")
                    )
                )
            ).limit(limit).all()
            
            return {
                "query": query,
                "results": fallback_results,
                "total_found": len(fallback_results),
                "search_method": "fallback_traditional",
                "llm_error": str(llm_error),
                "ai_explanation": f"LLM search failed, used traditional search as fallback. Found {len(fallback_results)} opportunities containing '{query}'.",
                "processing_time": time.time() - start_time
            }
    
    except Exception as e:
        logger.error(f"LLM search failed: {e}")
        raise HTTPException(status_code=500, detail=f"LLM search failed: {e}")


@router.post("/search/all-pages")
async def search_all_pages(
    query: str = Query(..., description="Search query"),
    max_results: int = Query(1000, ge=1, le=10000, description="Maximum results to return"),
    db: Session = Depends(get_db)
):
    """Search across ALL opportunities regardless of pagination."""
    
    search_conditions = []
    search_terms = query.lower().split()
    
    for term in search_terms:
        term_condition = or_(
            OpportunityModel.title.ilike(f"%{term}%"),
            OpportunityModel.description.ilike(f"%{term}%"),
            OpportunityModel.department.ilike(f"%{term}%"),
            OpportunityModel.eligibility_requirements.ilike(f"%{term}%")
        )
        search_conditions.append(term_condition)
    
    # Apply search across ALL active opportunities
    query_obj = db.query(OpportunityModel).filter(
        and_(
            OpportunityModel.is_active == True,
            *search_conditions
        )
    ).order_by(desc(OpportunityModel.scraped_at))
    
    # Get total count
    total_count = query_obj.count()
    
    # Get results up to max_results
    results = query_obj.limit(max_results).all()
    
    return {
        "query": query,
        "results": results,
        "total_found": total_count,
        "returned_count": len(results),
        "search_method": "all_pages",
        "message": f"Searched across all {total_count} opportunities"
    }


# =============================================================================
# EXISTING ENDPOINTS (keeping all original functionality)
# =============================================================================

# Simplified stats endpoint for frontend compatibility
@router.get("/stats")
async def get_stats_simple(db: Session = Depends(get_db)):
    """Get opportunity statistics (simplified endpoint for frontend compatibility)."""
    
    # Total counts
    total_opportunities = db.query(OpportunityModel).count()
    active_opportunities = db.query(OpportunityModel).filter(
        OpportunityModel.is_active == True
    ).count()
    inactive_opportunities = total_opportunities - active_opportunities
    
    # Count by type
    type_counts = db.query(
        OpportunityModel.opportunity_type,
        func.count(OpportunityModel.id)
    ).filter(
        OpportunityModel.is_active == True
    ).group_by(OpportunityModel.opportunity_type).all()
    
    # Recent opportunities (last 7 days)
    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_opportunities = db.query(OpportunityModel).filter(
        and_(
            OpportunityModel.scraped_at >= seven_days_ago,
            OpportunityModel.is_active == True
        )
    ).count()
    
    # Upcoming deadlines - opportunities with deadline information
    upcoming_deadlines = db.query(OpportunityModel).filter(
        and_(
            OpportunityModel.deadline.isnot(None),
            OpportunityModel.deadline != '',
            OpportunityModel.is_active == True
        )
    ).count()
    
    return {
        "total_opportunities": total_opportunities,
        "active_opportunities": active_opportunities,
        "inactive_opportunities": inactive_opportunities,
        "recent_opportunities": recent_opportunities,
        "upcoming_deadlines": upcoming_deadlines,
        "categories": [{"category": type_name, "count": count} for type_name, count in type_counts],
        "last_updated": datetime.now().isoformat()
    }

@router.get("/{opportunity_id}")
async def get_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific opportunity by ID."""
    
    opportunity = db.query(OpportunityModel).filter(
        OpportunityModel.id == opportunity_id
    ).first()
    
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    return opportunity


@router.post("/")
async def create_opportunity(
    opportunity: OpportunityCreate,
    db: Session = Depends(get_db)
):
    """Create a new opportunity (admin only)."""
    
    db_opportunity = OpportunityModel(
        title=opportunity.title,
        description=opportunity.description,
        department=opportunity.department,
        opportunity_type=opportunity.opportunity_type,
        eligibility_requirements=opportunity.eligibility_requirements,
        deadline=opportunity.deadline,
        funding_amount=opportunity.funding_amount,
        application_url=opportunity.application_url,
        source_url=opportunity.source_url,
        contact_email=opportunity.contact_email,
        tags=opportunity.tags or [],
        scraped_at=datetime.now(),
        is_active=True
    )
    
    db.add(db_opportunity)
    db.commit()
    db.refresh(db_opportunity)
    
    logger.info(f"Created new opportunity: {opportunity.title}")
    return db_opportunity


@router.put("/{opportunity_id}")
async def update_opportunity(
    opportunity_id: int,
    opportunity_update: OpportunityUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing opportunity (admin only)."""
    
    db_opportunity = db.query(OpportunityModel).filter(
        OpportunityModel.id == opportunity_id
    ).first()
    
    if not db_opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    # Update fields
    update_data = opportunity_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_opportunity, field, value)
    
    db.commit()
    db.refresh(db_opportunity)
    
    logger.info(f"Updated opportunity {opportunity_id}: {db_opportunity.title}")
    return db_opportunity


@router.delete("/{opportunity_id}")
async def delete_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db)
):
    """Delete an opportunity (admin only)."""
    
    db_opportunity = db.query(OpportunityModel).filter(
        OpportunityModel.id == opportunity_id
    ).first()
    
    if not db_opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    # Soft delete by marking as inactive
    db_opportunity.is_active = False
    db.commit()
    
    logger.info(f"Deleted (deactivated) opportunity {opportunity_id}: {db_opportunity.title}")
    return {"message": "Opportunity deleted successfully"}


# =============================================================================
# SCRAPING ENDPOINTS
# =============================================================================

@router.post("/scrape/start")
async def start_scraping(
    urls: Optional[List[str]] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """Start scraping all configured URLs or specific URLs."""
    
    logger.info("Starting scraping process...")
    
    try:
        if urls:
            logger.info(f"Scraping {len(urls)} specific URLs")
            results = await scraping_service.scrape_all_urls(urls)
        else:
            logger.info("Scraping all configured URLs from settings")
            results = await scraping_service.scrape_all_urls()
        
        # Calculate totals
        total_new = sum(r.get('opportunities_found', 0) for r in results if r.get('status') == 'success')
        total_failed = sum(1 for r in results if r.get('status') == 'failed')
        
        return {
            "message": "Scraping completed",
            "results": results,
            "summary": {
                "total_urls": len(results),
                "successful": len(results) - total_failed,
                "failed": total_failed,
                "total_opportunities_found": total_new
            }
        }
    
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scraping failed: {e}")


@router.post("/scrape-enhanced", response_model=ScrapingResponse)
async def trigger_enhanced_scraping(
    scraping_request: ScrapingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Trigger LLM-enhanced scraping with validation and enhancement."""
    
    logger.info("LLM-enhanced scraping triggered")
    
    # Check if LLM parsing is configured
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=400,
            detail="Gemini API key not configured. Please set GEMINI_API_KEY environment variable."
        )
    
    if not settings.enable_llm_parsing:
        logger.warning("LLM parsing is disabled. Enable with ENABLE_LLM_PARSING=true")
    
    if scraping_request.urls:
        # Scrape specific URLs with LLM enhancement
        results = []
        total_new = total_updated = total_failed = 0
        
        for url in scraping_request.urls:
            try:
                logger.info(f"Starting LLM-enhanced scraping for: {url}")
                result = await scraping_service.scrape_single_url(url)
                
                # Add LLM processing metadata to the result
                result['llm_enhanced'] = True
                result['llm_parsing_enabled'] = settings.enable_llm_parsing
                
                results.append(result)
                total_new += result.get('opportunities_found', 0)
                if result.get('status') == 'failed':
                    total_failed += 1
                    
            except Exception as e:
                logger.error(f"Failed to scrape {url} with LLM enhancement: {e}")
                results.append({
                    'url': url,
                    'status': 'failed',
                    'error': str(e),
                    'opportunities_found': 0,
                    'llm_enhanced': False
                })
                total_failed += 1
    else:
        # Scrape all configured websites with LLM enhancement
        logger.info("Starting LLM-enhanced scraping for all configured URLs")
        results = await scraping_service.scrape_all_urls()
        
        # Add LLM metadata to all results
        for result in results:
            result['llm_enhanced'] = True
            result['llm_parsing_enabled'] = settings.enable_llm_parsing
        
        total_new = sum(r.get('opportunities_found', 0) for r in results if r.get('status') == 'success')
        total_failed = sum(1 for r in results if r.get('status') == 'failed')
    
    # Calculate LLM processing statistics
    llm_stats = {
        'llm_parsing_enabled': settings.enable_llm_parsing,
        'gemini_configured': bool(settings.gemini_api_key),
        'opportunities_processed': sum(r.get('opportunities_found', 0) for r in results),
        'urls_processed': len(results)
    }
    
    return ScrapingResponse(
        message=f"LLM-enhanced scraping completed. LLM parsing: {'enabled' if settings.enable_llm_parsing else 'disabled'}",
        results=results,
        total_new=total_new,
        total_updated=0,  # Updated opportunities not tracked in this version
        total_failed=total_failed,
        metadata=llm_stats
    )


# =============================================================================
# EXISTING STATS AND UTILITY ENDPOINTS
# =============================================================================

@router.get("/stats/overview", response_model=OpportunityStats)
async def get_opportunity_stats(db: Session = Depends(get_db)):
    """Get opportunity statistics."""
    
    # Total counts
    total_opportunities = db.query(OpportunityModel).count()
    active_opportunities = db.query(OpportunityModel).filter(
        OpportunityModel.is_active == True
    ).count()
    
    # Count by type
    type_counts = db.query(
        OpportunityModel.opportunity_type,
        func.count(OpportunityModel.id)
    ).filter(
        OpportunityModel.is_active == True
    ).group_by(OpportunityModel.opportunity_type).all()
    
    opportunities_by_type = {type_name: count for type_name, count in type_counts}
    
    # Count by department
    dept_counts = db.query(
        OpportunityModel.department,
        func.count(OpportunityModel.id)
    ).filter(
        and_(
            OpportunityModel.is_active == True,
            OpportunityModel.department.isnot(None)
        )
    ).group_by(OpportunityModel.department).limit(10).all()
    
    opportunities_by_department = {dept: count for dept, count in dept_counts}
    
    # Recent opportunities (last 7 days)
    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_opportunities = db.query(OpportunityModel).filter(
        and_(
            OpportunityModel.scraped_at >= seven_days_ago,
            OpportunityModel.is_active == True
        )
    ).count()
    
    # Upcoming deadlines (next 30 days)
    # Since deadlines are now text-based, count opportunities with deadline information
    upcoming_deadlines = db.query(OpportunityModel).filter(
        and_(
            OpportunityModel.deadline.isnot(None),
            OpportunityModel.deadline != '',
            OpportunityModel.is_active == True
        )
    ).count()
    
    return OpportunityStats(
        total_opportunities=total_opportunities,
        active_opportunities=active_opportunities,
        opportunities_by_type=opportunities_by_type,
        opportunities_by_department=opportunities_by_department,
        recent_opportunities=recent_opportunities,
        upcoming_deadlines=upcoming_deadlines
    )


@router.get("/departments/list")
async def get_departments(db: Session = Depends(get_db)):
    """Get list of all departments with opportunity counts."""
    
    departments = db.query(
        OpportunityModel.department,
        func.count(OpportunityModel.id).label('count')
    ).filter(
        and_(
            OpportunityModel.is_active == True,
            OpportunityModel.department.isnot(None)
        )
    ).group_by(OpportunityModel.department).all()
    
    return [
        {"name": dept, "count": count}
        for dept, count in departments
        if dept  # Filter out None/empty departments
    ]


@router.get("/recent")
async def get_recent_opportunities(
    days: int = Query(7, ge=1, le=30, description="Number of days to look back"),
    limit: int = Query(20, ge=1, le=10000, description="Number of opportunities to return"),
    db: Session = Depends(get_db)
):
    """Get recently added opportunities."""
    
    cutoff_date = datetime.now() - timedelta(days=days)
    
    opportunities = db.query(OpportunityModel).filter(
        and_(
            OpportunityModel.scraped_at >= cutoff_date,
            OpportunityModel.is_active == True
        )
    ).order_by(desc(OpportunityModel.scraped_at)).limit(limit).all()
    
    return opportunities


@router.get("/deadlines/upcoming")
async def get_upcoming_deadlines(
    days: int = Query(30, ge=1, le=90, description="Number of days to look ahead"),
    limit: int = Query(20, ge=1, le=10000, description="Number of opportunities to return"),
    db: Session = Depends(get_db)
):
    """Get opportunities with upcoming deadlines (NOTE: now returns opportunities with any deadline text)."""
    
    # Since deadlines are now text-based, we can't do date filtering
    # Instead, return opportunities that have deadline information
    opportunities = db.query(OpportunityModel).filter(
        and_(
            OpportunityModel.deadline.isnot(None),
            OpportunityModel.deadline != '',
            OpportunityModel.is_active == True
        )
    ).order_by(desc(OpportunityModel.scraped_at)).limit(limit).all()
    
    return opportunities 