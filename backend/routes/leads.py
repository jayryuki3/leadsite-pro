"""Lead discovery, management, and ranking routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, or_
from typing import Optional, List
from pydantic import BaseModel
import httpx
import json

from database import get_db
from models.lead import Lead, LeadDetail
from models.activity import Activity
from routes.settings import get_setting_value

router = APIRouter(prefix="/leads", tags=["leads"])


# ── Category Mappings ─────────────────────────────────────────────

CATEGORY_MAP = {
    "restaurant": ["restaurant", "meal_delivery", "meal_takeaway"],
    "cafe": ["cafe", "bakery", "coffee_shop"],
    "bar": ["bar", "night_club", "liquor_store"],
    "salon": ["hair_care", "beauty_salon"],
    "spa": ["spa"],
    "gym": ["gym"],
    "dentist": ["dentist"],
    "doctor": ["doctor", "health"],
    "veterinarian": ["veterinary_care"],
    "lawyer": ["lawyer"],
    "accountant": ["accounting"],
    "real_estate": ["real_estate_agency"],
    "insurance": ["insurance_agency"],
    "car_dealer": ["car_dealer"],
    "car_repair": ["car_repair", "car_wash"],
    "plumber": ["plumber"],
    "electrician": ["electrician"],
    "roofing": ["roofing_contractor"],
    "painter": ["painter"],
    "locksmith": ["locksmith"],
    "moving": ["moving_company"],
    "storage": ["storage"],
    "laundry": ["laundry"],
    "pet_store": ["pet_store"],
    "florist": ["florist"],
    "jewelry": ["jewelry_store"],
    "clothing": ["clothing_store", "shoe_store"],
    "electronics": ["electronics_store"],
    "furniture": ["furniture_store", "home_goods_store"],
    "pharmacy": ["pharmacy"],
    "convenience": ["convenience_store"],
    "supermarket": ["supermarket", "grocery_or_supermarket"],
    "hotel": ["lodging"],
    "travel": ["travel_agency"],
}


# ── Schemas ───────────────────────────────────────────────────────

class DiscoverRequest(BaseModel):
    location: str  # "lat,lng" or address
    radius: int = 5000  # meters
    categories: List[str] = ["restaurant"]
    keyword: Optional[str] = None


class StatusUpdate(BaseModel):
    status: str


class BulkDeleteRequest(BaseModel):
    confirm: bool = False


# ── Discovery ─────────────────────────────────────────────────────

@router.post("/discover")
async def discover_businesses(req: DiscoverRequest, db: AsyncSession = Depends(get_db)):
    """Discover businesses via Google Places API."""
    api_key = await get_setting_value(db, "google_places_api_key")
    if not api_key:
        raise HTTPException(status_code=400, detail="Google Places API key not configured")

    # Gather all Google place types from selected categories
    place_types = []
    for cat in req.categories:
        place_types.extend(CATEGORY_MAP.get(cat, [cat]))
    place_types = list(set(place_types))

    all_places = []
    seen_place_ids = set()

    # Check existing leads to dedup
    existing_result = await db.execute(select(Lead.place_id).where(Lead.place_id.isnot(None)))
    existing_ids = {row[0] for row in existing_result.fetchall()}

    async with httpx.AsyncClient(timeout=30.0) as client:
        for ptype in place_types:
            params = {
                "key": api_key,
                "location": req.location,
                "radius": req.radius,
                "type": ptype,
            }
            if req.keyword:
                params["keyword"] = req.keyword

            resp = await client.get(
                "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                params=params,
            )

            if resp.status_code != 200:
                continue

            data = resp.json()
            results = data.get("results", [])

            for place in results:
                pid = place.get("place_id", "")
                if pid in seen_place_ids or pid in existing_ids:
                    continue
                seen_place_ids.add(pid)

                # Determine category from the first matching type
                detected_cat = "other"
                place_types_list = place.get("types", [])
                for cat_name, cat_types in CATEGORY_MAP.items():
                    if any(t in place_types_list for t in cat_types):
                        detected_cat = cat_name
                        break

                loc = place.get("geometry", {}).get("location", {})

                lead = Lead(
                    place_id=pid,
                    name=place.get("name", "Unknown"),
                    address=place.get("vicinity", ""),
                    phone=place.get("formatted_phone_number", ""),
                    website=place.get("website", ""),
                    rating=place.get("rating", 0.0),
                    review_count=place.get("user_ratings_total", 0),
                    category=detected_cat,
                    lat=loc.get("lat", 0.0),
                    lng=loc.get("lng", 0.0),
                    status="new",
                    photo_ref=place.get("photos", [{}])[0].get("photo_reference", "") if place.get("photos") else "",
                )
                db.add(lead)
                all_places.append({
                    "name": lead.name,
                    "address": lead.address,
                    "category": lead.category,
                    "rating": lead.rating,
                    "review_count": lead.review_count,
                    "website": lead.website,
                    "lat": lead.lat,
                    "lng": lead.lng,
                })

    await db.commit()

    # Log activity
    activity = Activity(
        action="discovery_scan",
        description=f"Discovered {len(all_places)} businesses near {req.location}",
        metadata_json={"categories": req.categories, "radius": req.radius, "found": len(all_places)},
    )
    db.add(activity)
    await db.commit()

    return {
        "found": len(all_places),
        "businesses": all_places,
    }


# ── List / Filter / Sort ──────────────────────────────────────────

@router.get("/")
async def list_leads(
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    page: int = 1,
    per_page: int = 25,
):
    """List leads with filtering, sorting, and pagination."""
    query = select(Lead)

    if status:
        query = query.where(Lead.status == status)
    if category:
        query = query.where(Lead.category == category)
    if search:
        query = query.where(
            or_(
                Lead.name.ilike(f"%{search}%"),
                Lead.address.ilike(f"%{search}%"),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Sort
    sort_col = getattr(Lead, sort_by, Lead.created_at)
    if sort_dir == "asc":
        query = query.order_by(asc(sort_col))
    else:
        query = query.order_by(desc(sort_col))

    # Paginate
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    leads = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "leads": [
            {
                "id": l.id,
                "name": l.name,
                "address": l.address,
                "phone": l.phone,
                "website": l.website,
                "rating": l.rating,
                "review_count": l.review_count,
                "category": l.category,
                "status": l.status,
                "audit_score": l.audit_score,
                "opportunity_score": l.opportunity_score,
                "lat": l.lat,
                "lng": l.lng,
                "created_at": str(l.created_at) if l.created_at else None,
            }
            for l in leads
        ],
    }


# ── Categories ────────────────────────────────────────────────────

@router.get("/categories")
async def get_categories():
    """Return all supported business categories with Google type mappings."""
    return {
        "categories": [
            {"key": k, "label": k.replace("_", " ").title(), "google_types": v}
            for k, v in CATEGORY_MAP.items()
        ]
    }


# ── Stats ─────────────────────────────────────────────────────────

@router.get("/stats")
async def get_lead_stats(db: AsyncSession = Depends(get_db)):
    """Get lead counts by status and category."""
    # By status
    status_result = await db.execute(
        select(Lead.status, func.count(Lead.id)).group_by(Lead.status)
    )
    by_status = {row[0]: row[1] for row in status_result.fetchall()}

    # By category
    cat_result = await db.execute(
        select(Lead.category, func.count(Lead.id)).group_by(Lead.category)
    )
    by_category = {row[0]: row[1] for row in cat_result.fetchall()}

    # Total
    total_result = await db.execute(select(func.count(Lead.id)))
    total = total_result.scalar()

    return {
        "total": total,
        "by_status": by_status,
        "by_category": by_category,
    }


# ── Single Lead ───────────────────────────────────────────────────

@router.get("/{lead_id}")
async def get_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single lead with full details."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Get enriched details if they exist
    detail_result = await db.execute(select(LeadDetail).where(LeadDetail.lead_id == lead_id))
    detail = detail_result.scalar_one_or_none()

    lead_data = {
        "id": lead.id,
        "place_id": lead.place_id,
        "name": lead.name,
        "address": lead.address,
        "phone": lead.phone,
        "email": lead.email,
        "website": lead.website,
        "rating": lead.rating,
        "review_count": lead.review_count,
        "category": lead.category,
        "status": lead.status,
        "audit_score": lead.audit_score,
        "opportunity_score": lead.opportunity_score,
        "lat": lead.lat,
        "lng": lead.lng,
        "photo_ref": lead.photo_ref,
        "notes": lead.notes,
        "created_at": str(lead.created_at) if lead.created_at else None,
        "updated_at": str(lead.updated_at) if lead.updated_at else None,
    }

    if detail:
        lead_data["detail"] = {
            "description": detail.description,
            "services": detail.services,
            "hours": detail.hours,
            "owner_name": detail.owner_name,
            "top_reviews": detail.top_reviews,
            "photos_local": detail.photos_local,
            "brand_colors": detail.brand_colors,
            "logo_path": detail.logo_path,
            "yelp_url": detail.yelp_url,
            "audit_data": detail.audit_data,
            "tech_stack": detail.tech_stack,
        }
    else:
        lead_data["detail"] = None

    return lead_data


# ── Status Update ─────────────────────────────────────────────────

@router.patch("/{lead_id}/status")
async def update_lead_status(lead_id: int, req: StatusUpdate, db: AsyncSession = Depends(get_db)):
    """Update a lead's pipeline status."""
    valid_statuses = ["new", "audited", "prospect", "mockup_sent", "contacted", "responded", "closed_won", "closed_lost"]
    if req.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    old_status = lead.status
    lead.status = req.status

    activity = Activity(
        action="status_change",
        description=f"{lead.name}: {old_status} -> {req.status}",
        lead_id=lead_id,
        metadata_json={"old_status": old_status, "new_status": req.status},
    )
    db.add(activity)
    await db.commit()

    return {"id": lead_id, "status": req.status}


# ── Delete ────────────────────────────────────────────────────────

@router.delete("/{lead_id}")
async def delete_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a single lead and its details."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Delete associated detail
    detail_result = await db.execute(select(LeadDetail).where(LeadDetail.lead_id == lead_id))
    detail = detail_result.scalar_one_or_none()
    if detail:
        await db.delete(detail)

    name = lead.name
    await db.delete(lead)

    activity = Activity(
        action="lead_deleted",
        description=f"Deleted lead: {name}",
        lead_id=lead_id,
    )
    db.add(activity)
    await db.commit()

    return {"deleted": lead_id}


# ── Bulk Delete ───────────────────────────────────────────────────

@router.delete("/")
async def bulk_delete_leads(req: BulkDeleteRequest, db: AsyncSession = Depends(get_db)):
    """Delete all leads. Requires confirm=true."""
    if not req.confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true to delete all leads")

    # Count first
    count_result = await db.execute(select(func.count(Lead.id)))
    count = count_result.scalar()

    # Delete all details first
    all_details = await db.execute(select(LeadDetail))
    for d in all_details.scalars().all():
        await db.delete(d)

    # Delete all leads
    all_leads = await db.execute(select(Lead))
    for l in all_leads.scalars().all():
        await db.delete(l)

    activity = Activity(
        action="bulk_delete",
        description=f"Deleted all {count} leads",
        metadata_json={"count": count},
    )
    db.add(activity)
    await db.commit()

    return {"deleted": count}


# ── Ranking ───────────────────────────────────────────────────────

@router.post("/rank")
async def rank_leads(db: AsyncSession = Depends(get_db)):
    """Recalculate opportunity scores for all leads using a 4-factor weighted algorithm."""
    # Load category weights from settings
    cat_weights_str = await get_setting_value(db, "category_weights")
    try:
        cat_weights = json.loads(cat_weights_str) if cat_weights_str else {}
    except (json.JSONDecodeError, TypeError):
        cat_weights = {}

    result = await db.execute(select(Lead))
    leads = result.scalars().all()
    ranked = 0

    for lead in leads:
        # Factor 1: Category value (0-25)
        cat_weight = cat_weights.get(lead.category, 5) / 10  # Normalize 1-10 -> 0.1-1.0
        category_score = cat_weight * 25

        # Factor 2: Website deficiency (0-30)
        if not lead.website:
            website_score = 30  # No website = highest opportunity
        elif lead.audit_score is not None:
            # Lower audit score = higher opportunity
            website_score = max(0, 30 - (lead.audit_score * 0.3))
        else:
            website_score = 15  # Has website but not audited

        # Factor 3: Review signal (0-25)
        if lead.review_count > 0:
            # High reviews + high rating = established business that can pay
            review_signal = min(25, (lead.review_count / 100) * 15 + (lead.rating / 5) * 10)
        else:
            review_signal = 5  # Unknown

        # Factor 4: Competition gap (0-20)
        # Businesses with moderate reviews but poor web presence
        if not lead.website and lead.review_count > 10:
            competition_score = 20
        elif lead.audit_score and lead.audit_score < 50 and lead.review_count > 5:
            competition_score = 15
        elif lead.audit_score and lead.audit_score < 70:
            competition_score = 10
        else:
            competition_score = 5

        lead.opportunity_score = round(category_score + website_score + review_signal + competition_score, 1)
        ranked += 1

    await db.commit()

    activity = Activity(
        action="leads_ranked",
        description=f"Recalculated opportunity scores for {ranked} leads",
        metadata_json={"ranked": ranked},
    )
    db.add(activity)
    await db.commit()

    return {"ranked": ranked}


# ── Scraping Route ────────────────────────────────────────────────

@router.post("/{lead_id}/scrape")
async def scrape_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Scrape and enrich a lead with Yelp + website data."""
    from services.scraper import enrich_lead
    
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    yelp_key = await get_setting_value(db, "yelp_api_key")
    
    enriched = await enrich_lead(
        lead_name=lead.name,
        lead_address=lead.address,
        lead_website=lead.website or "",
        yelp_api_key=yelp_key,
    )
    
    # Upsert LeadDetail
    detail_result = await db.execute(select(LeadDetail).where(LeadDetail.lead_id == lead_id))
    detail = detail_result.scalar_one_or_none()
    
    if detail is None:
        detail = LeadDetail(lead_id=lead_id)
        db.add(detail)
    
    detail.description = enriched["description"]
    detail.services = enriched["services"]
    detail.hours = enriched["hours"]
    detail.owner_name = enriched["owner_name"]
    detail.top_reviews = enriched["top_reviews"]
    detail.photos_local = enriched["photos"]
    detail.brand_colors = enriched["brand_colors"]
    detail.logo_path = enriched["logo_url"]
    detail.yelp_url = enriched["yelp_url"]
    
    if lead.status in ("new", "audited"):
        lead.status = "prospect"
    
    activity = Activity(
        action="lead_enriched",
        description=f"Scraped business info for {lead.name}",
        lead_id=lead_id,
        metadata_json={"services_found": len(enriched['services']), "reviews_found": len(enriched['top_reviews'])},
    )
    db.add(activity)
    await db.commit()
    
    return {
        "lead_id": lead_id,
        "name": lead.name,
        "enriched": enriched,
    }
