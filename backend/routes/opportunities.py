"""
Opportunities API routes
"""

from flask import Blueprint, request, jsonify
from sqlalchemy import and_, or_, func, desc, text
from sqlalchemy.orm import Query
from datetime import datetime, timedelta
from typing import List, Dict, Any

from models import db, Opportunity

opportunities_bp = Blueprint('opportunities', __name__)


@opportunities_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "opportunities"})


@opportunities_bp.route('/', methods=['GET'])
def get_opportunities():
    """Get paginated research opportunities with full-text search support."""
    try:
        # Parse query parameters
        page = int(request.args.get('page', 1))
        skip = int(request.args.get('skip', 0))  # Support both skip and page parameters
        limit = int(request.args.get('limit', 20))
        search_query = request.args.get('search', '').strip()
        category = request.args.get('category', '').strip()
        department = request.args.get('department', '').strip()
        has_funding = request.args.get('has_funding', '').lower() == 'true'
        
        # Start with base query
        query = db.session.query(Opportunity).filter(Opportunity.is_active == True)
        
        # Apply search filter using full-text search
        if search_query:
            # Convert search query to tsquery format
            # Handle simple queries and phrases
            if '"' in search_query:
                # Handle phrase search
                tsquery = search_query.replace('"', "'")
            else:
                # Handle individual terms with OR logic
                terms = search_query.split()
                tsquery = ' | '.join(terms)
            
            try:
                # Use full-text search with ranking
                query = query.filter(
                    Opportunity.search_vector.op('@@')(func.to_tsquery('english', tsquery))
                ).order_by(
                    desc(func.ts_rank(Opportunity.search_vector, func.to_tsquery('english', tsquery)))
                )
            except Exception as e:
                # Fallback to basic text search if full-text search fails
                search_terms = f"%{search_query}%"
                query = query.filter(
                    or_(
                        Opportunity.title.ilike(search_terms),
                        Opportunity.description.ilike(search_terms),
                        Opportunity.department.ilike(search_terms)
                    )
                )
        else:
            # Default ordering by scraped_at (newest first)
            query = query.order_by(desc(Opportunity.scraped_at))
        
        # Apply category filter
        if category:
            query = query.filter(Opportunity.opportunity_type.ilike(f"%{category}%"))
        
        # Apply department filter
        if department:
            query = query.filter(Opportunity.department.ilike(f"%{department}%"))
        
        # Apply funding filter
        if has_funding:
            query = query.filter(and_(
                Opportunity.funding_amount.isnot(None),
                Opportunity.funding_amount != ''
            ))
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination - use skip if provided, otherwise calculate from page
        offset = skip if skip > 0 else (page - 1) * limit
        opportunities = query.offset(offset).limit(limit).all()
        
        # Convert to dict format
        opportunities_data = []
        for opp in opportunities:
            opp_dict = opp.to_dict()
            # Add computed fields for backward compatibility
            opp_dict['category'] = opp.opportunity_type
            opp_dict['url'] = opp.application_url
            opp_dict['requirements'] = opp.eligibility_requirements
            opportunities_data.append(opp_dict)
        
        return jsonify({
            "opportunities": opportunities_data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total_count,
                "pages": (total_count + limit - 1) // limit
            }
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to fetch opportunities: {str(e)}"}), 500


@opportunities_bp.route('/search', methods=['GET'])
def search_opportunities():
    """Search opportunities using full-text search with ranking."""
    try:
        query_text = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 10))
        
        if not query_text:
            return jsonify({"opportunities": [], "total": 0})
        
        # Prepare the search query for PostgreSQL full-text search
        # Handle simple queries and phrases
        if '"' in query_text:
            # Handle phrase search
            tsquery = query_text.replace('"', "'")
        else:
            # Handle individual terms with OR logic for broader results
            terms = query_text.split()
            tsquery = ' | '.join(terms)
        
        try:
            # Use full-text search with ranking
            opportunities = db.session.query(Opportunity).filter(
                and_(
                    Opportunity.is_active == True,
                    Opportunity.search_vector.op('@@')(func.to_tsquery('english', tsquery))
                )
            ).order_by(
                desc(func.ts_rank(Opportunity.search_vector, func.to_tsquery('english', tsquery)))
            ).limit(limit).all()
            
        except Exception as search_error:
            # Fallback to basic ILIKE search if full-text search fails
            search_terms = f"%{query_text}%"
            opportunities = db.session.query(Opportunity).filter(
                and_(
                    Opportunity.is_active == True,
                    or_(
                        Opportunity.title.ilike(search_terms),
                        Opportunity.description.ilike(search_terms),
                        Opportunity.department.ilike(search_terms)
                    )
                )
            ).order_by(desc(Opportunity.scraped_at)).limit(limit).all()
        
        # Convert to dict format
        opportunities_data = []
        for opp in opportunities:
            opp_dict = opp.to_dict()
            # Add computed fields for backward compatibility
            opp_dict['category'] = opp.opportunity_type
            opp_dict['url'] = opp.application_url
            opp_dict['requirements'] = opp.eligibility_requirements
            opportunities_data.append(opp_dict)
        
        return jsonify({
            "opportunities": opportunities_data,
            "total": len(opportunities_data)
        })
        
    except Exception as e:
        return jsonify({"error": f"Search failed: {str(e)}"}), 500


@opportunities_bp.route('/stats', methods=['GET'])
def get_opportunity_stats():
    """Get opportunity statistics including recent new opportunities."""
    try:
        # Get total active opportunities
        total_active = db.session.query(Opportunity).filter(
            Opportunity.is_active == True
        ).count()
        
        # Get opportunities by status
        status_counts = db.session.query(
            Opportunity.status,
            func.count(Opportunity.id).label('count')
        ).filter(
            Opportunity.is_active == True
        ).group_by(Opportunity.status).all()
        
        # Get recent new opportunities (last 7 days)
        cutoff_date = datetime.now() - timedelta(days=7)
        recent_new = db.session.query(Opportunity).filter(
            and_(
                Opportunity.first_seen_at >= cutoff_date,
                or_(Opportunity.status == 'new', Opportunity.status == 'active'),
                Opportunity.is_active == True
            )
        ).count()
        
        # Get opportunities with funding
        funded_count = db.session.query(Opportunity).filter(
            and_(
                Opportunity.is_active == True,
                Opportunity.funding_amount.isnot(None),
                Opportunity.funding_amount != ''
            )
        ).count()
        
        # Get top departments
        top_departments = db.session.query(
            Opportunity.department,
            func.count(Opportunity.id).label('count')
        ).filter(
            and_(
                Opportunity.is_active == True,
                Opportunity.department.isnot(None),
                Opportunity.department != ''
            )
        ).group_by(Opportunity.department).order_by(
            desc(func.count(Opportunity.id))
        ).limit(10).all()
        
        return jsonify({
            "total_active": total_active,
            "recent_new_opportunities": recent_new,
            "funded_opportunities": funded_count,
            "status_breakdown": {
                status: count for status, count in status_counts
            },
            "top_departments": [
                {"department": dept, "count": count} 
                for dept, count in top_departments
            ]
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to fetch stats: {str(e)}"}), 500


@opportunities_bp.route('/recent-new', methods=['GET'])
def get_recent_new_opportunities():
    """Get recently discovered opportunities."""
    try:
        days = int(request.args.get('days', 7))
        limit = int(request.args.get('limit', 50))
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        opportunities = db.session.query(Opportunity).filter(
            and_(
                Opportunity.first_seen_at >= cutoff_date,
                or_(Opportunity.status == 'new', Opportunity.status == 'active'),
                Opportunity.is_active == True
            )
        ).order_by(desc(Opportunity.first_seen_at)).limit(limit).all()
        
        # Convert to dict format
        opportunities_data = []
        for opp in opportunities:
            opp_dict = opp.to_dict()
            # Add computed fields for backward compatibility
            opp_dict['category'] = opp.opportunity_type
            opp_dict['url'] = opp.application_url
            opp_dict['requirements'] = opp.eligibility_requirements
            opportunities_data.append(opp_dict)
        
        return jsonify({
            "opportunities": opportunities_data,
            "total": len(opportunities_data),
            "days": days
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to fetch recent opportunities: {str(e)}"}), 500 