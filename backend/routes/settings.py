"""Settings API routes - manages API keys, business info, search config, and pricing tiers."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models.settings import Setting
from services.encryption import encrypt_value, decrypt_value

router = APIRouter()

# ── Pydantic Schemas ──────────────────────────────────────────────────────

class SettingUpdate(BaseModel):
    value: str

class SettingsBulkUpdate(BaseModel):
    settings: Dict[str, Any]

class PricingTier(BaseModel):
    name: str
    display_name: str
    price: float
    price_type: str  # "flat" or "monthly"
    features: List[str]
    description: str

class CategoryWeight(BaseModel):
    category: str
    weight: float  # 0-100

# ── Default Values ────────────────────────────────────────────────────────

DEFAULT_SETTINGS = {
    # API Keys
    "google_places_api_key": {"value": "", "encrypted": True, "category": "api_keys"},
    "openai_api_key": {"value": "", "encrypted": True, "category": "api_keys"},
    "ai_base_url": {"value": "https://api.openai.com/v1", "encrypted": False, "category": "api_keys"},
    "openai_model": {"value": "gpt-4o", "encrypted": False, "category": "api_keys"},
    "yelp_api_key": {"value": "", "encrypted": True, "category": "api_keys"},
    
    # Business Info
    "business_name": {"value": "", "encrypted": False, "category": "business_info"},
    "business_email": {"value": "", "encrypted": False, "category": "business_info"},
    "business_phone": {"value": "", "encrypted": False, "category": "business_info"},
    "business_website": {"value": "", "encrypted": False, "category": "business_info"},
    "business_logo_path": {"value": "", "encrypted": False, "category": "business_info"},
    "calendly_link": {"value": "", "encrypted": False, "category": "business_info"},
    
    # Search Configuration
    "search_latitude": {"value": "37.7749", "encrypted": False, "category": "search"},
    "search_longitude": {"value": "-122.4194", "encrypted": False, "category": "search"},
    "search_radius_miles": {"value": "10", "encrypted": False, "category": "search"},
    "search_zip_code": {"value": "", "encrypted": False, "category": "search"},
    
    # SMTP Configuration
    "smtp_host": {"value": "", "encrypted": False, "category": "email"},
    "smtp_port": {"value": "587", "encrypted": False, "category": "email"},
    "smtp_username": {"value": "", "encrypted": False, "category": "email"},
    "smtp_password": {"value": "", "encrypted": True, "category": "email"},
    "smtp_from_name": {"value": "", "encrypted": False, "category": "email"},
    "smtp_from_email": {"value": "", "encrypted": False, "category": "email"},
    
    # AI Prompts
    "mockup_system_prompt": {"value": "", "encrypted": False, "category": "ai_prompts"},
}

DEFAULT_PRICING_TIERS = [
    {
        "name": "starter",
        "display_name": "Starter",
        "price": 497,
        "price_type": "flat",
        "description": "Perfect for businesses that need a simple online presence",
        "features": [
            "1-3 page responsive website",
            "Mobile-friendly design",
            "Contact form",
            "Basic SEO setup",
            "Google Maps embed",
            "Social media links"
        ]
    },
    {
        "name": "professional",
        "display_name": "Professional",
        "price": 1497,
        "price_type": "flat",
        "description": "For businesses ready to grow their online presence",
        "features": [
            "5-8 page custom website",
            "Online booking/scheduling",
            "Photo gallery",
            "Customer testimonials",
            "Google Analytics integration",
            "Advanced SEO optimization",
            "Social media integration"
        ]
    },
    {
        "name": "premium",
        "display_name": "Premium",
        "price": 2997,
        "price_type": "flat",
        "description": "Full-featured website for maximum impact",
        "features": [
            "10-15 page website",
            "E-commerce or advanced booking",
            "Custom forms & workflows",
            "Blog with CMS",
            "Speed optimization",
            "Schema markup for rich results",
            "Priority support"
        ]
    },
    {
        "name": "retainer",
        "display_name": "Monthly Retainer",
        "price": 149,
        "price_type": "monthly",
        "description": "Ongoing website management (12-month contract)",
        "features": [
            "Website hosting & SSL",
            "Monthly content updates",
            "Uptime monitoring & backups",
            "Minor design tweaks",
            "Monthly performance report",
            "Priority email support",
            "Annual value: $1,788/year"
        ]
    }
]

DEFAULT_CATEGORY_WEIGHTS = {
    "electrician": 95, "plumber": 95, "contractor": 95, "hvac": 92,
    "roofer": 90, "landscaper": 85, "painter": 85, "handyman": 82,
    "auto_repair": 80, "dentist": 88, "chiropractor": 85, "veterinarian": 82,
    "salon": 82, "barber": 78, "spa": 80, "photographer": 88,
    "personal_trainer": 82, "cleaning_service": 80, "pet_groomer": 78,
    "moving_company": 80, "pest_control": 82, "locksmith": 78,
    "restaurant": 65, "cafe": 60, "bakery": 65,
    "dry_cleaner": 40, "laundromat": 25, "gas_station": 20,
    "parking_lot": 15, "vending": 10,
}

# ── Helper Functions ──────────────────────────────────────────────────────

async def get_setting_value(db: AsyncSession, key: str) -> Optional[str]:
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if setting is None:
        default = DEFAULT_SETTINGS.get(key)
        return default["value"] if default else None
    if setting.is_encrypted and setting.value:
        try:
            return decrypt_value(setting.value)
        except Exception:
            return setting.value
    return setting.value


async def set_setting_value(db: AsyncSession, key: str, value: str, category: str = "general"):
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    
    is_encrypted = DEFAULT_SETTINGS.get(key, {}).get("encrypted", False)
    store_value = encrypt_value(value) if is_encrypted and value else value
    
    if setting is None:
        setting = Setting(
            key=key,
            value=store_value,
            is_encrypted=1 if is_encrypted else 0,
            category=category,
        )
        db.add(setting)
    else:
        setting.value = store_value
        setting.is_encrypted = 1 if is_encrypted else 0

# ── Routes ──────────────────────────────────────────────────────────────

@router.get("/")
async def get_all_settings(db: AsyncSession = Depends(get_db)):
    """Get all settings grouped by category."""
    result = await db.execute(select(Setting))
    db_settings = {s.key: s for s in result.scalars().all()}
    
    settings = {}
    for key, default in DEFAULT_SETTINGS.items():
        category = default["category"]
        if category not in settings:
            settings[category] = {}
        
        if key in db_settings:
            s = db_settings[key]
            if s.is_encrypted and s.value:
                try:
                    val = decrypt_value(s.value)
                    # Mask encrypted values for display
                    settings[category][key] = {
                        "value": val[:2] + "*" * (len(val) - 4) + val[-2:] if len(val) > 4 else "****",
                        "has_value": True,
                        "is_encrypted": True,
                    }
                except Exception:
                    settings[category][key] = {"value": "", "has_value": False, "is_encrypted": True}
            else:
                settings[category][key] = {
                    "value": s.value or "",
                    "has_value": bool(s.value),
                    "is_encrypted": False,
                }
        else:
            settings[category][key] = {
                "value": default["value"],
                "has_value": bool(default["value"]),
                "is_encrypted": default.get("encrypted", False),
            }
    
    return {"settings": settings}


@router.put("/")
async def update_settings_bulk(data: SettingsBulkUpdate, db: AsyncSession = Depends(get_db)):
    """Update multiple settings at once."""
    for key, value in data.settings.items():
        default = DEFAULT_SETTINGS.get(key)
        category = default["category"] if default else "general"
        await set_setting_value(db, key, str(value), category)
    return {"success": True, "updated": list(data.settings.keys())}


# ── Pricing Tiers ─────────────────────────────────────────────────────────

@router.get("/pricing")
async def get_pricing_tiers(db: AsyncSession = Depends(get_db)):
    """Get pricing tiers."""
    result = await db.execute(select(Setting).where(Setting.key == "pricing_tiers"))
    setting = result.scalar_one_or_none()
    if setting and setting.value:
        return {"tiers": json.loads(setting.value)}
    return {"tiers": DEFAULT_PRICING_TIERS}


@router.put("/pricing")
async def update_pricing_tiers(tiers: List[PricingTier], db: AsyncSession = Depends(get_db)):
    """Update pricing tiers."""
    tiers_json = json.dumps([t.model_dump() for t in tiers])
    await set_setting_value(db, "pricing_tiers", tiers_json, "pricing")
    return {"success": True}


# ── Category Weights ──────────────────────────────────────────────────────

@router.get("/category-weights")
async def get_category_weights(db: AsyncSession = Depends(get_db)):
    """Get category value weights for ranking."""
    result = await db.execute(select(Setting).where(Setting.key == "category_weights"))
    setting = result.scalar_one_or_none()
    if setting and setting.value:
        return {"weights": json.loads(setting.value)}
    return {"weights": DEFAULT_CATEGORY_WEIGHTS}


@router.put("/category-weights")
async def update_category_weights(weights: Dict[str, float], db: AsyncSession = Depends(get_db)):
    """Update category weights."""
    await set_setting_value(db, "category_weights", json.dumps(weights), "ranking")
    return {"success": True}


# ── API Key Testing ───────────────────────────────────────────────────────

@router.post("/test/{provider}")
async def test_api_key(provider: str, db: AsyncSession = Depends(get_db)):
    """Test if an API key is valid."""
    import httpx
    
    if provider == "google_places":
        key = await get_setting_value(db, "google_places_api_key")
        if not key:
            raise HTTPException(status_code=400, detail="Google Places API key not configured")
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://places.googleapis.com/v1/places:searchNearby",
                headers={"X-Goog-Api-Key": key, "X-Goog-FieldMask": "places.id"},
                params={},
            )
            # A 400 with INVALID_ARGUMENT means key works but request is bad (expected)
            if resp.status_code in [200, 400]:
                return {"valid": True, "provider": provider}
            return {"valid": False, "provider": provider, "error": resp.text}
    
    elif provider == "openai":
        key = (await get_setting_value(db, "openai_api_key") or "").strip()
        base_url = (await get_setting_value(db, "ai_base_url") or "https://api.openai.com/v1").rstrip("/")
        is_local = any(h in base_url for h in ["localhost", "127.0.0.1", "0.0.0.0", ":11434"])
        if not key and not is_local:
            raise HTTPException(status_code=400, detail="AI API key not configured")
        headers = {}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        # Normalize URL for /models endpoint
        if base_url.endswith("/chat/completions"):
            models_url = base_url.rsplit("/chat/completions", 1)[0] + "/models"
        elif base_url.endswith("/v1"):
            models_url = f"{base_url}/models"
        else:
            models_url = f"{base_url}/v1/models"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(models_url, headers=headers)
                return {"valid": resp.status_code == 200, "provider": provider}
        except httpx.ConnectError:
            return {"valid": False, "provider": provider, "error": f"Cannot connect to {models_url}"}
    
    elif provider == "yelp":
        key = await get_setting_value(db, "yelp_api_key")
        if not key:
            raise HTTPException(status_code=400, detail="Yelp API key not configured")
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.yelp.com/v3/businesses/search",
                headers={"Authorization": f"Bearer {key}"},
                params={"location": "San Francisco", "limit": 1},
            )
            return {"valid": resp.status_code == 200, "provider": provider}
    
    raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")


# ── AI Model List (OpenAI-compatible) ─────────────────────────────────────

@router.get("/openai-models")
async def get_openai_models(db: AsyncSession = Depends(get_db)):
    """Fetch available models from any OpenAI-compatible API."""
    import httpx
    key = (await get_setting_value(db, "openai_api_key") or "").strip()
    base_url = (await get_setting_value(db, "ai_base_url") or "https://api.openai.com/v1").rstrip("/")
    is_local = any(h in base_url for h in ["localhost", "127.0.0.1", "0.0.0.0", ":11434"])
    
    if not key and not is_local:
        return {"models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]}
    
    headers = {}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    
    # Normalize URL for /models endpoint
    if base_url.endswith("/chat/completions"):
        models_url = base_url.rsplit("/chat/completions", 1)[0] + "/models"
    elif base_url.endswith("/v1"):
        models_url = f"{base_url}/models"
    else:
        models_url = f"{base_url}/v1/models"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(models_url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                # Handle both OpenAI format {"data": [...]} and Ollama format {"models": [...]}
                model_list = data.get("data") or data.get("models") or []
                models = sorted([
                    m.get("id") or m.get("name") or m.get("model", "")
                    for m in model_list
                    if m.get("id") or m.get("name") or m.get("model")
                ])
                return {"models": models if models else ["gpt-4o", "gpt-4o-mini"]}
    except Exception:
        pass
    
    return {"models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]}


# ── Single Setting (catch-all — MUST be last to avoid shadowing named routes) ─

@router.get("/raw/{key}")
async def get_setting_raw(key: str, db: AsyncSession = Depends(get_db)):
    """Get the raw (decrypted) value of a setting. Used internally."""
    value = await get_setting_value(db, key)
    return {"key": key, "value": value}


@router.put("/{key}")
async def update_setting(key: str, data: SettingUpdate, db: AsyncSession = Depends(get_db)):
    """Update a single setting. This route is last because {key} matches any path segment."""
    default = DEFAULT_SETTINGS.get(key)
    category = default["category"] if default else "general"
    await set_setting_value(db, key, data.value, category)
    return {"success": True, "key": key}