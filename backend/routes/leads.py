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


# ── Geocoding Helper ──────────────────────────────────────────────

import re as _re

_LATLNG_RE = _re.compile(r'^\s*(-?\d+\.?\d*),\s*(-?\d+\.?\d*)\s*$')


async def _geocode_location(location: str, api_key: str) -> str:
    """Convert a text address to 'lat,lng'. Pass-through if already lat,lng."""
    if _LATLNG_RE.match(location):
        return location.strip()

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": location, "key": api_key},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Geocoding request failed")
        data = resp.json()
        if data.get("status") != "OK" or not data.get("results"):
            raise HTTPException(
                status_code=400,
                detail=f"Could not geocode '{location}'. Try a more specific address or use GPS.",
            )
        loc = data["results"][0]["geometry"]["location"]
        return f"{loc['lat']},{loc['lng']}"


# ── Discovery ─────────────────────────────────────────────────────

@router.post("/discover")
async def discover_businesses(req: DiscoverRequest, db: AsyncSession = Depends(get_db)):
    """Discover businesses via Google Places API."""
    api_key = await get_setting_value(db, "google_places_api_key")
    if not api_key:
        raise HTTPException(status_code=400, detail="Google Places API key not configured. Add it in Settings.")

    # Geocode text addresses to lat,lng
    latlng = await _geocode_location(req.location, api_key)

    # Gather all Google place types from selected categories
    place_types = []
    for cat in req.categories:
        place_types.extend(CATEGORY_MAP.get(cat, [cat]))
    place_types = list(set(place_types))

    all_places = []
    seen_place_ids = set()
    api_errors = []  # Collect errors to surface to the user

    # Check existing leads to dedup
    existing_result = await db.execute(select(Lead.place_id).where(Lead.place_id.isnot(None)))
    existing_ids = {row[0] for row in existing_result.fetchall()}

    async with httpx.AsyncClient(timeout=30.0) as client:
        # -- Step 1: Nearby Search to find place_ids --
        for ptype in place_types:
            params = {
                "key": api_key,
                "location": latlng,
                "radius": req.radius,
                "type": ptype,
            }
            if req.keyword:
                params["keyword"] = req.keyword

            try:
                resp = await client.get(
                    "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
                    params=params,
                )
            except Exception as e:
                api_errors.append(f"Network error for type '{ptype}': {str(e)}")
                continue

            if resp.status_code != 200:
                api_errors.append(f"HTTP {resp.status_code} for type '{ptype}'")
                continue

            data = resp.json()
            api_status = data.get("status", "UNKNOWN")
            if api_status == "ZERO_RESULTS":
                continue
            if api_status != "OK":
                error_msg = data.get("error_message", api_status)
                api_errors.append(f"Google API [{api_status}]: {error_msg}")
                continue

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

                all_places.append({
                    "place_id": pid,
                    "name": place.get("name", "Unknown"),
                    "address": place.get("vicinity", ""),
                    "category": detected_cat,
                    "rating": place.get("rating", 0.0),
                    "review_count": place.get("user_ratings_total", 0),
                    "lat": loc.get("lat", 0.0),
                    "lng": loc.get("lng", 0.0),
                    "photo_ref": place.get("photos", [{}])[0].get("photo_reference", "") if place.get("photos") else "",
                    # These come from Place Details, not Nearby Search
                    "phone": "",
                    "website": "",
                })

        # ── Step 2: Place Details for phone & website (batch, capped) ──
        # Limit detail lookups to avoid quota burn (max 60 per scan)
        detail_places = all_places[:60]
        for p in detail_places:
            try:
                detail_resp = await client.get(
                    "https://maps.googleapis.com/maps/api/place/details/json",
                    params={
                        "key": api_key,
                        "place_id": p["place_id"],
                        "fields": "formatted_phone_number,website,formatted_address",
                    },
                )
                if detail_resp.status_code == 200:
                    detail_data = detail_resp.json().get("result", {})
                    p["phone"] = detail_data.get("formatted_phone_number", "")
                    p["website"] = detail_data.get("website", "")
                    if detail_data.get("formatted_address"):
                        p["address"] = detail_data["formatted_address"]
            except Exception:
                pass  # Keep what we have from Nearby Search

    # ── Step 3: Save leads to DB ──
    saved = []
    for p in all_places:
        lead = Lead(
            place_id=p["place_id"],
            name=p["name"],
            address=p["address"],
            phone=p["phone"],
            website=p["website"],
            rating=p["rating"],
            review_count=p["review_count"],
            category=p["category"],
            lat=p["lat"],
            lng=p["lng"],
            status="new",
            photo_ref=p["photo_ref"],
        )
        db.add(lead)
        saved.append({
            "name": p["name"],
            "address": p["address"],
            "category": p["category"],
            "rating": p["rating"],
            "review_count": p["review_count"],
            "website": p["website"],
            "lat": p["lat"],
            "lng": p["lng"],
        })

    await db.commit()

    # Log activity
    activity = Activity(
        action="discovery_scan",
        description=f"Discovered {len(saved)} businesses near {req.location}",
        metadata_json={"categories": req.categories, "radius": req.radius, "found": len(saved)},
    )
    db.add(activity)
    await db.commit()

    response = {
        "found": len(saved),
        "businesses": saved,
    }
    # Surface API errors so the user knows WHY results are empty
    if api_errors:
        response["api_errors"] = list(set(api_errors))[:5]  # Dedupe, cap at 5
    if not saved and api_errors:
        # If we got zero results AND there were API errors, raise so the frontend shows the toast
        raise HTTPException(
            status_code=502,
            detail=f"Google Places API error: {api_errors[0]}",
        )
    return response


# ── List / Filter / Sort ──────────────────────────────────────────

@router.get("/")
async def list_leads(
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    sort_order: Optional[str] = None,
    page: Optional[int] = None,
    per_page: int = 25,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
):
    """List leads with filtering, sorting, and pagination.

    Accepts both pagination styles:
      - page/per_page (1-indexed pages)
      - offset/limit  (direct offset)
    Also accepts sort_order as alias for sort_dir.
    """
    # Accept sort_order as alias for sort_dir
    effective_sort_dir = sort_order or sort_dir

    # Resolve pagination: offset/limit takes priority if provided
    if offset is not None:
        effective_offset = offset
        effective_limit = limit or per_page
    else:
        effective_page = page or 1
        effective_limit = limit or per_page
        effective_offset = (effective_page - 1) * effective_limit

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
    if effective_sort_dir == "asc":
        query = query.order_by(asc(sort_col))
    else:
        query = query.order_by(desc(sort_col))

    # Paginate
    query = query.offset(effective_offset).limit(effective_limit)

    result = await db.execute(query)
    leads = result.scalars().all()

    return {
        "total": total,
        "page": page or (effective_offset // effective_limit + 1),
        "per_page": effective_limit,
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
                "website_quality_score": l.website_quality_score if l.website_quality_score is not None else -1,
                "audit_score": l.audit_score,
                "audit_details": l.audit_details,
                "opportunity_score": l.opportunity_score,
                "google_maps_url": l.google_maps_url,
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
