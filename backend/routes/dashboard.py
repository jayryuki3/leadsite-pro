"""Dashboard API routes - pipeline stats, activity feed, revenue tracking."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models.lead import Lead
from models.mockup import Mockup
from models.email_draft import EmailDraft
from models.activity import Activity

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get full pipeline statistics."""
    # Lead counts by status
    status_query = select(Lead.status, func.count(Lead.id)).group_by(Lead.status)
    status_result = await db.execute(status_query)
    status_counts = dict(status_result.all())
    
    total_leads = sum(status_counts.values())
    
    # Audit stats
    audited = await db.execute(select(func.count(Lead.id)).where(Lead.website_quality_score >= 0))
    no_website = await db.execute(select(func.count(Lead.id)).where(Lead.website_quality_score == 0))
    avg_score = await db.execute(select(func.avg(Lead.website_quality_score)).where(Lead.website_quality_score > 0))
    
    # Mockup count
    mockup_count = await db.execute(select(func.count(Mockup.id)))
    
    # Email stats
    email_total = await db.execute(select(func.count(EmailDraft.id)))
    email_sent = await db.execute(select(func.count(EmailDraft.id)).where(EmailDraft.status == "sent"))
    email_draft = await db.execute(select(func.count(EmailDraft.id)).where(EmailDraft.status == "draft"))
    
    # Category distribution
    cat_query = select(Lead.category, func.count(Lead.id)).group_by(Lead.category).order_by(func.count(Lead.id).desc()).limit(10)
    cat_result = await db.execute(cat_query)
    top_categories = [{"category": cat.replace('_', ' ').title(), "count": count} for cat, count in cat_result.all()]
    
    # Funnel data
    funnel = [
        {"stage": "Discovered", "count": total_leads},
        {"stage": "Audited", "count": audited.scalar() or 0},
        {"stage": "Prospects", "count": status_counts.get("prospect", 0) + status_counts.get("mockup_created", 0) + status_counts.get("contacted", 0) + status_counts.get("responded", 0) + status_counts.get("converted", 0)},
        {"stage": "Mockups", "count": mockup_count.scalar() or 0},
        {"stage": "Contacted", "count": (email_sent.scalar() or 0)},
        {"stage": "Responded", "count": status_counts.get("responded", 0)},
        {"stage": "Converted", "count": status_counts.get("converted", 0)},
    ]
    
    return {
        "total_leads": total_leads,
        "status_counts": status_counts,
        "audited": audited.scalar() or 0,
        "no_website": no_website.scalar() or 0,
        "avg_website_score": round(avg_score.scalar() or 0, 1),
        "mockup_count": mockup_count.scalar() or 0,
        "email_total": email_total.scalar() or 0,
        "email_sent": email_sent.scalar() or 0,
        "email_drafts": email_draft.scalar() or 0,
        "top_categories": top_categories,
        "funnel": funnel,
    }


@router.get("/activity")
async def get_recent_activity(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Get recent activity feed."""
    result = await db.execute(
        select(Activity)
        .order_by(Activity.created_at.desc())
        .limit(limit)
    )
    activities = result.scalars().all()
    
    return {
        "activities": [
            {
                "id": a.id,
                "action": a.action,
                "description": a.description,
                "lead_id": a.lead_id,
                "created_at": str(a.created_at) if a.created_at else None,
            }
            for a in activities
        ]
    }


@router.get("/revenue")
async def get_revenue_data(db: AsyncSession = Depends(get_db)):
    """Get revenue tracking data based on converted leads."""
    converted = await db.execute(
        select(func.count(Lead.id)).where(Lead.status == "converted")
    )
    converted_count = converted.scalar() or 0
    
    # Placeholder revenue estimates based on conversion assumptions
    return {
        "converted_leads": converted_count,
        "estimated_revenue": {
            "starter": {"count": 0, "total": 0},
            "professional": {"count": 0, "total": 0},
            "premium": {"count": 0, "total": 0},
            "retainer": {"count": 0, "monthly": 0, "annual": 0},
        },
        "total_revenue": 0,
        "monthly_recurring": 0,
    }
