"""
Opportunities routes for Flask application
Converted from FastAPI opportunities router
"""

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import and_, or_, func, desc, asc, text
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import os

# Optional Gemini support (same style as llm_validation_service)
try:
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore
    GEMINI_AVAILABLE = True
except ImportError:  # pragma: no cover
    GEMINI_AVAILABLE = False

from models import db, Opportunity, ScrapingLog
from config import get_settings
from auth import require_auth, require_auth_optional, get_auth_info

# Disable strict_slashes so routes work both with and without trailing slash (avoids 308 redirects)
opportunities_bp = Blueprint('opportunities', __name__)

def get_query_param(param_name: str, default_value=None, param_type=str):
    """Helper function to get query parameters with type conversion."""
    value = request.args.get(param_name, default_value)
    if value is None:
        return default_value
    
    if param_type == int:
        try:
            return int(value)
        except ValueError:
            return default_value
    elif param_type == bool:
        # Handle case where value is already a boolean (from default_value)
        if isinstance(value, bool):
            return value
        # Handle string values from query parameters
        return value.lower() in ('true', '1', 'yes', 'on')
    elif param_type == float:
        try:
            return float(value)
        except ValueError:
            return default_value
    
    return value

@opportunities_bp.route('/')
@require_auth
def get_opportunities():
    """Get opportunities with filtering and pagination."""
    
    # Parse query parameters
    skip = get_query_param('skip', 0, int)
    limit = get_query_param('limit', 20, int)
    department = get_query_param('department')
    opportunity_type = get_query_param('opportunity_type')
    is_active = get_query_param('is_active', True, bool)
    deadline_from = get_query_param('deadline_from')
    deadline_to = get_query_param('deadline_to')
    has_funding = get_query_param('has_funding', None, bool)
    search = get_query_param('search')
    sort_by = get_query_param('sort_by', 'scraped_at')
    sort_order = get_query_param('sort_order', 'desc')
    
    # Validate parameters
    if skip < 0:
        skip = 0
    if limit < 1 or limit > 10000:
        limit = 20
    if sort_order not in ['asc', 'desc']:
        sort_order = 'desc'
    
    try:
        query = db.session.query(Opportunity)
        
        # Apply filters
        if is_active is not None:
            query = query.filter(Opportunity.is_active == is_active)
        
        if department:
            query = query.filter(Opportunity.department.ilike(f"%{department}%"))
        
        if opportunity_type:
            query = query.filter(Opportunity.opportunity_type == opportunity_type)
        
        if has_funding is not None:
            if has_funding:
                query = query.filter(Opportunity.funding_amount.isnot(None))
            else:
                query = query.filter(Opportunity.funding_amount.is_(None))
        
        if search:
            search_filter = or_(
                Opportunity.title.ilike(f"%{search}%"),
                Opportunity.description.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        # Apply sorting
        if hasattr(Opportunity, sort_by):
            sort_column = getattr(Opportunity, sort_by)
            if sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
        
        # Apply pagination
        opportunities = query.offset(skip).limit(limit).all()
        
        # Convert to dictionaries
        result = [opp.to_dict() for opp in opportunities]
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error getting opportunities: {e}")
        return jsonify({"error": "Failed to retrieve opportunities", "message": str(e)}), 500

@opportunities_bp.route('/count')
@require_auth
def get_opportunities_count():
    """Return total count of active opportunities."""
    try:
        total = db.session.query(Opportunity).filter(Opportunity.is_active == True).count()
        return jsonify({"total": total})
    except Exception as e:
        current_app.logger.error(f"Error getting opportunities count: {e}")
        return jsonify({"error": "Failed to get count", "message": str(e)}), 500

@opportunities_bp.route('/<int:opportunity_id>')
@require_auth
def get_opportunity(opportunity_id):
    """Get a single opportunity by ID."""
    try:
        opportunity = db.session.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
        
        if not opportunity:
            return jsonify({"error": "Opportunity not found"}), 404
        
        return jsonify(opportunity.to_dict())
        
    except Exception as e:
        current_app.logger.error(f"Error getting opportunity {opportunity_id}: {e}")
        return jsonify({"error": "Failed to retrieve opportunity", "message": str(e)}), 500

@opportunities_bp.route('/', methods=['POST'])
@require_auth
def create_opportunity():
    """Create a new opportunity."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate required fields
        if not data.get('title'):
            return jsonify({"error": "Title is required"}), 400
        if not data.get('source_url'):
            return jsonify({"error": "Source URL is required"}), 400
        
        # Create new opportunity
        opportunity = Opportunity(
            title=data.get('title'),
            description=data.get('description'),
            department=data.get('department'),
            opportunity_type=data.get('opportunity_type'),
            eligibility_requirements=data.get('eligibility_requirements'),
            deadline=data.get('deadline'),
            funding_amount=data.get('funding_amount'),
            application_url=data.get('application_url'),
            source_url=data.get('source_url'),
            contact_email=data.get('contact_email'),
            tags=data.get('tags', []),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(opportunity)
        db.session.commit()
        
        return jsonify(opportunity.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating opportunity: {e}")
        return jsonify({"error": "Failed to create opportunity", "message": str(e)}), 500

@opportunities_bp.route('/<int:opportunity_id>', methods=['PUT'])
@require_auth
def update_opportunity(opportunity_id):
    """Update an existing opportunity."""
    try:
        opportunity = db.session.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
        
        if not opportunity:
            return jsonify({"error": "Opportunity not found"}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Update fields if provided
        for field in ['title', 'description', 'department', 'opportunity_type', 
                     'eligibility_requirements', 'deadline', 'funding_amount',
                     'application_url', 'source_url', 'contact_email', 'tags', 'is_active']:
            if field in data:
                setattr(opportunity, field, data[field])
        
        db.session.commit()
        
        return jsonify(opportunity.to_dict())
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating opportunity {opportunity_id}: {e}")
        return jsonify({"error": "Failed to update opportunity", "message": str(e)}), 500

@opportunities_bp.route('/<int:opportunity_id>', methods=['DELETE'])
@require_auth
def delete_opportunity(opportunity_id):
    """Delete an opportunity."""
    try:
        opportunity = db.session.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
        
        if not opportunity:
            return jsonify({"error": "Opportunity not found"}), 404
        
        db.session.delete(opportunity)
        db.session.commit()
        
        return jsonify({"message": f"Opportunity {opportunity_id} deleted successfully"})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting opportunity {opportunity_id}: {e}")
        return jsonify({"error": "Failed to delete opportunity", "message": str(e)}), 500

@opportunities_bp.route('/stats')
@require_auth
def get_stats():
    """Get comprehensive statistics about opportunities."""
    try:
        total_count = db.session.query(Opportunity).count()
        active_count = db.session.query(Opportunity).filter(Opportunity.is_active == True).count()
        inactive_count = total_count - active_count

        # Recent opportunities (last 7 days based on scraped_at)
        recent_cutoff = datetime.now() - timedelta(days=7)
        recent_count = db.session.query(Opportunity).filter(
            Opportunity.scraped_at >= recent_cutoff,
            Opportunity.is_active == True
        ).count()

        # Upcoming deadlines (next 30 days)
        deadline_now_dt = datetime.now()
        deadline_cutoff_dt = deadline_now_dt + timedelta(days=30)

        # Convert comparison dates to ISO strings (YYYY-MM-DD) to avoid casting errors on text columns
        deadline_now_str = deadline_now_dt.strftime("%Y-%m-%d")
        deadline_cutoff_str = deadline_cutoff_dt.strftime("%Y-%m-%d")

        upcoming_deadline_count = db.session.query(Opportunity).filter(
            Opportunity.deadline.isnot(None),
            Opportunity.deadline >= deadline_now_str,
            Opportunity.deadline <= deadline_cutoff_str,
            Opportunity.is_active == True
        ).count()

        # Category breakdown (opportunity_type)
        category_counts = db.session.query(
            Opportunity.opportunity_type.label("category"),
            func.count(Opportunity.id).label("count")
        ).group_by(Opportunity.opportunity_type).all()

        categories_list = [
            {
                "category": cat.category if cat.category else "Unknown",
                "count": cat.count
            }
            for cat in category_counts
        ]

        stats = {
            "total_opportunities": total_count,
            "active_opportunities": active_count,
            "inactive_opportunities": inactive_count,
            "recent_opportunities": recent_count,
            "upcoming_deadlines": upcoming_deadline_count,
            "categories": categories_list,
            # Additional metadata
            "departments": db.session.query(func.count(Opportunity.department.distinct())).scalar(),
            "with_funding": db.session.query(Opportunity).filter(Opportunity.funding_amount.isnot(None)).count(),
            "last_updated": datetime.now().isoformat(),
        }

        return jsonify(stats)
        
    except Exception as e:
        current_app.logger.error(f"Error getting stats: {e}")
        return jsonify({"error": "Failed to get statistics", "message": str(e)}), 500

@opportunities_bp.route('/departments/list')
@require_auth
def get_departments():
    """Get list of all departments."""
    try:
        departments = db.session.query(Opportunity.department).filter(
            Opportunity.department.isnot(None),
            Opportunity.is_active == True
        ).distinct().all()
        
        department_list = [dept[0] for dept in departments if dept[0]]
        
        return jsonify({
            "departments": sorted(department_list),
            "count": len(department_list)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting departments: {e}")
        return jsonify({"error": "Failed to get departments", "message": str(e)}), 500

@opportunities_bp.route('/recent')
@require_auth
def get_recent_opportunities():
    """Get recently added opportunities."""
    days = get_query_param('days', 7, int)
    limit = get_query_param('limit', 20, int)
    
    if days < 1 or days > 30:
        days = 7
    if limit < 1 or limit > 10000:
        limit = 20
    
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        
        opportunities = db.session.query(Opportunity).filter(
            Opportunity.scraped_at >= cutoff_date,
            Opportunity.is_active == True
        ).order_by(desc(Opportunity.scraped_at)).limit(limit).all()
        
        result = [opp.to_dict() for opp in opportunities]
        
        return jsonify({
            "opportunities": result,
            "total": len(result),
            "days_back": days,
            "cutoff_date": cutoff_date.isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting recent opportunities: {e}")
        return jsonify({"error": "Failed to get recent opportunities", "message": str(e)}), 500

# Admin endpoints
@opportunities_bp.route('/admin/delete-all', methods=['DELETE'])
@require_auth
def delete_all_opportunities():
    """Delete ALL opportunities from the database (DESTRUCTIVE OPERATION)."""
    confirm = get_query_param('confirm')
    
    if confirm != 'DELETE_ALL':
        return jsonify({
            "error": "Confirmation required",
            "message": "Must provide confirm='DELETE_ALL' to delete all opportunities"
        }), 400
    
    try:
        total_count = db.session.query(Opportunity).count()
        deleted_count = db.session.query(Opportunity).delete()
        db.session.commit()
        
        current_app.logger.warning(f"DELETED ALL {deleted_count} opportunities from database")
        
        return jsonify({
            "message": f"Successfully deleted ALL {deleted_count} opportunities",
            "previous_total": total_count,
            "deleted_count": deleted_count
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete all opportunities: {e}")
        return jsonify({"error": "Failed to delete opportunities", "message": str(e)}), 500

@opportunities_bp.route('/admin/delete-inactive', methods=['DELETE'])
@require_auth
def delete_inactive_opportunities():
    """Delete all inactive opportunities."""
    try:
        deleted_count = db.session.query(Opportunity).filter(
            Opportunity.is_active == False
        ).delete()
        db.session.commit()
        
        current_app.logger.info(f"Deleted {deleted_count} inactive opportunities")
        
        return jsonify({"message": f"Deleted {deleted_count} inactive opportunities"})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete inactive opportunities: {e}")
        return jsonify({"error": "Failed to delete inactive opportunities", "message": str(e)}), 500 

@opportunities_bp.route('/search')
@require_auth
def search_opportunities():
    """Advanced search with multiple filters."""
    # This endpoint is not fully implemented in the original file,
    # so it's added here as a placeholder.
    # It would require a more complex query building logic.
    return jsonify({"message": "Search opportunities endpoint is not fully implemented yet."}), 501

@opportunities_bp.route('/scrape', methods=['POST'])
@require_auth
def trigger_scrape():
    """Trigger scraping for opportunities."""
    # This endpoint is not fully implemented in the original file,
    # so it's added here as a placeholder.
    # It would require a scraping logic.
    return jsonify({"message": "Scrape opportunities endpoint is not fully implemented yet."}), 501

@opportunities_bp.route('/search/llm', methods=['POST'])
@require_auth
def llm_search():
    """LLM-powered semantic search using Google Gemini.

    Query parameters:
      • query – search string (required)
      • limit – max number of cards to return (default 20, max 100)

    Response JSON matches the structure consumed by the React front-end:
    {
      "results": [Opportunity, …],
      "total_found": int,
      "ai_explanation": str,
      "query": str,
      "processing_time": int  # ms
    }
    """
    start_time = datetime.now()

    query_str = request.args.get('query', '').strip()
    try:
        limit = min(max(int(request.args.get('limit', 20)), 1), 100)
    except ValueError:
        limit = 20

    if not query_str:
        return jsonify({
            "results": [],
            "total_found": 0,
            "ai_explanation": "Empty query – nothing to search.",
            "query": query_str,
            "processing_time": 0
        })

    # ------------------------------------------------------------------
    # 1) Try Gemini semantic search
    # ------------------------------------------------------------------
    gemini_key = os.getenv("GEMINI_API_KEY")
    if GEMINI_AVAILABLE and gemini_key:
        try:
            client = genai.Client(api_key=gemini_key)
            model_name = os.getenv("GEMINI_MODEL", "gemma-3-27b-it")

            sys_prompt = (
                "You are a helpful assistant that turns a user search query into a JSON "
                "response containing a summary and a list of Stanford research "
                "opportunity cards. Output *ONLY* valid JSON with this exact schema:\n\n"
                "{\n"
                "  \"ai_explanation\": <string – 1-2 sentence summary of the kinds of opportunities found in the list below. Mention specific themes or departments if they stand out.>,\n"
                "  \"opportunities\": [\n"
                "    {\n"
                "      \"title\": <string>,\n"
                "      \"description\": <string>,\n"
                "      \"department\": <string or null>,\n"
                "      \"opportunity_type\": <string or null>,\n"
                "      \"deadline\": <YYYY-MM-DD or null>,\n"
                "      \"funding_amount\": <string or null>,\n"
                "      \"application_url\": <string – https URL>,\n"
                "      \"tags\": [ <string>, … ]\n"
                "    } /* repeat up to {limit} items */\n"
                "  ]\n"
                "}\n\n"
                "If you don't know a field, output null.\n"
                "Do NOT wrap the JSON in markdown fences or any extra text."
            )

            user_prompt = f"Search query: {query_str}\nMax results: {limit}"

            response = client.models.generate_content(
                model=model_name,
                contents=[sys_prompt, user_prompt],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=4096,
                ),
                # request_options={'timeout': 120}
            )
            raw_text = response.text.strip()

            # Attempt to parse JSON out of reply – Gemini might sometimes wrap it
            import json, re
            try:
                parsed_json = json.loads(raw_text)
            except json.JSONDecodeError:
                # Try to extract the first JSON object in the text
                match = re.search(r"{.*}", raw_text, re.S)
                if match:
                    parsed_json = json.loads(match.group(0))
                else:
                    raise

            opp_cards = parsed_json.get("opportunities", [])[:limit]
            # Ensure each card has required keys so frontend doesn't crash
            standardised = []
            for card in opp_cards:
                standardised.append({
                    "title": card.get("title", "Untitled"),
                    "description": card.get("description", ""),
                    "department": card.get("department"),
                    "opportunity_type": card.get("opportunity_type"),
                    "deadline": card.get("deadline"),
                    "funding_amount": card.get("funding_amount"),
                    "application_url": card.get("application_url"),
                    "source_url": card.get("application_url"),  # alias for FE mapping
                    "tags": card.get("tags", []),
                    "is_active": True,
                    # minimal extras for transformOpportunity()
                    "scraped_at": datetime.now().isoformat()
                })

            elapsed_s = (datetime.now() - start_time).total_seconds()
            return jsonify({
                "results": standardised,
                "total_found": len(standardised),
                "ai_explanation": parsed_json.get("ai_explanation", ""),
                "query": query_str,
                "processing_time": elapsed_s
            })
        except Exception as e:
            current_app.logger.error(f"Gemini search failed: {e}")
            # Fall through to keyword fallback

    # ------------------------------------------------------------------
    # 2) Fallback – keyword search in DB
    # ------------------------------------------------------------------
    current_app.logger.info("Using keyword fallback for LLM search")
    try:
        search_filter = or_(
            Opportunity.title.ilike(f"%{query_str}%"),
            Opportunity.description.ilike(f"%{query_str}%")
        )
        matches_q = db.session.query(Opportunity).filter(
            search_filter,
            Opportunity.is_active == True
        ).order_by(desc(Opportunity.scraped_at)).limit(limit)
        matches = [opp.to_dict() for opp in matches_q]
        elapsed_s = (datetime.now() - start_time).total_seconds()
        return jsonify({
            "results": matches,
            "total_found": len(matches),
            "ai_explanation": "Fallback keyword search – Gemini unavailable or errored.",
            "query": query_str,
            "processing_time": elapsed_s
        })
    except Exception as e:
        current_app.logger.error(f"Keyword fallback search failed: {e}")
        return jsonify({
            "results": [],
            "total_found": 0,
            "ai_explanation": "Search failed due to server error.",
            "query": query_str,
            "processing_time": 0,
            "error": str(e)
        }), 500

# Add auth info endpoint for debugging
@opportunities_bp.route('/auth/info')
@require_auth_optional
def auth_info():
    """Get authentication configuration info (for debugging)."""
    info = get_auth_info()
    info['endpoint'] = 'opportunities.auth_info'
    info['authenticated'] = bool(request.headers.get('X-API-Key'))
    return jsonify(info) 