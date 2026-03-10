"""AI API routes - OpenAI-powered intelligence across the app."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
import json
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models.lead import Lead, LeadDetail
from routes.settings import get_setting_value, DEFAULT_CATEGORY_WEIGHTS

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None

class LocationRequest(BaseModel):
    location: str


async def call_openai(db: AsyncSession, system_prompt: str, user_message: str, max_tokens: int = 1000) -> str:
    """Helper to call any OpenAI-compatible API (OpenAI, Ollama, OpenRouter, Chutes, etc)."""
    import httpx
    
    api_key = await get_setting_value(db, "openai_api_key")
    base_url = (await get_setting_value(db, "ai_base_url") or "https://api.openai.com/v1").rstrip("/")
    model = await get_setting_value(db, "openai_model") or "gpt-4o"
    
    if not api_key:
        raise HTTPException(status_code=400, detail="AI API key not configured. Go to Settings.")
    
    headers = {"Content-Type": "application/json"}
    # Some local servers (Ollama) don't need auth; only add if key is non-empty
    if api_key.strip():
        headers["Authorization"] = f"Bearer {api_key}"
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7,
            },
        )
        
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"AI API error ({base_url}): {resp.text}")
        
        data = resp.json()
        return data["choices"][0]["message"]["content"]


@router.post("/chat")
async def ai_chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """General AI chat with pipeline context."""
    # Build context from database
    from sqlalchemy import func as sqlfunc
    total = (await db.execute(select(sqlfunc.count(Lead.id)))).scalar()
    audited = (await db.execute(select(sqlfunc.count(Lead.id)).where(Lead.website_quality_score >= 0))).scalar()
    no_site = (await db.execute(select(sqlfunc.count(Lead.id)).where(Lead.website_quality_score == 0))).scalar()
    
    # Get top leads
    top_leads = await db.execute(select(Lead).order_by(Lead.opportunity_score.desc()).limit(10))
    top_list = [{"name": l.name, "category": l.category, "score": l.opportunity_score, "website_score": l.website_quality_score} for l in top_leads.scalars().all()]
    
    system_prompt = f"""You are LeadSite Pro AI Assistant. You help a web designer find and convert local business leads.

Current Pipeline Stats:
- Total leads: {total}
- Audited: {audited}
- No website: {no_site}

Top 10 leads by opportunity score:
{json.dumps(top_list, indent=2)}

You can help with:
- Prioritizing leads
- Writing follow-up emails
- Suggesting outreach strategies
- Explaining rankings
- General web design business advice

Be concise and actionable."""
    
    response = await call_openai(db, system_prompt, req.message)
    return {"response": response}


@router.post("/suggest-categories")
async def suggest_categories(req: LocationRequest, db: AsyncSession = Depends(get_db)):
    """AI suggests best categories to target for a location."""
    system_prompt = """You are a business consultant. Given a location, suggest the top 8-12 business categories that would benefit most from having a professional website built for them. Consider:
1. Service businesses that rely on local customers finding them online
2. Businesses where a website provides significant value (bookings, portfolio, reviews)
3. Categories where many businesses still lack good websites

Return ONLY a JSON array of category keys from this list:
electrician, plumber, contractor, hvac, roofer, landscaper, painter, handyman, auto_repair, dentist, chiropractor, veterinarian, salon, barber, spa, photographer, personal_trainer, cleaning_service, pet_groomer, moving_company, pest_control, locksmith, restaurant, cafe, bakery, dry_cleaner, laundromat, gas_station, real_estate, insurance, accounting, lawyer, gym, yoga

Example: ["electrician", "plumber", "dentist", "salon"]"""
    
    response = await call_openai(db, system_prompt, f"Location: {req.location}", max_tokens=200)
    
    try:
        # Extract JSON array from response
        import re
        match = re.search(r'\[.*?\]', response, re.DOTALL)
        if match:
            categories = json.loads(match.group())
            return {"categories": categories}
    except Exception:
        pass
    
    return {"categories": ["electrician", "plumber", "contractor", "hvac", "dentist", "salon", "auto_repair", "landscaper"]}


@router.post("/analyze-audit/{lead_id}")
async def analyze_audit(lead_id: int, db: AsyncSession = Depends(get_db)):
    """AI analysis of a lead's website audit results."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if lead.website_quality_score == -1:
        raise HTTPException(status_code=400, detail="Lead has not been audited yet")
    
    system_prompt = """You are a website audit expert. Analyze the audit results for a local business website and provide:
1. A brief plain-English summary of the website's strengths and weaknesses
2. The top 3 most impactful improvements they should make
3. A one-sentence pitch for why they need a new website

Keep it concise (150 words max). Format with clear sections."""
    
    audit_data = json.dumps(lead.audit_details, indent=2) if lead.audit_details else "No website found"
    user_msg = f"""Business: {lead.name} ({lead.category})
Website: {lead.website or 'None'}
Quality Score: {lead.website_quality_score}/100
Rating: {lead.rating} ({lead.review_count} reviews)

Audit Details:
{audit_data}"""
    
    response = await call_openai(db, system_prompt, user_msg, max_tokens=500)
    return {"analysis": response, "lead_id": lead_id}


@router.post("/explain-ranking/{lead_id}")
async def explain_ranking(lead_id: int, db: AsyncSession = Depends(get_db)):
    """AI explanation of why a lead ranked where it did."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    weights = DEFAULT_CATEGORY_WEIGHTS
    
    system_prompt = """You are explaining a lead's opportunity ranking to a web designer. The ranking uses 4 factors:
- Category Value (40%): How much the business type benefits from a website
- Website Deficiency (30%): How poor their current site is (or if they have none)
- Review Signal (15%): High reviews + poor site = big opportunity
- Competition Gap (15%): Competitors with better sites = this business is losing customers

Explain in 2-3 sentences why this lead scored what it did, and whether it's worth pursuing. Be direct and actionable."""
    
    user_msg = f"""Business: {lead.name}
Category: {lead.category} (category value weight: {weights.get(lead.category, 50)}/100)
Opportunity Score: {lead.opportunity_score}/100
Website Quality: {lead.website_quality_score}/100 {'(no website!)' if lead.website_quality_score == 0 else ''}
Rating: {lead.rating} stars, {lead.review_count} reviews
Website: {lead.website or 'None'}"""
    
    response = await call_openai(db, system_prompt, user_msg, max_tokens=300)
    return {"explanation": response, "lead_id": lead_id}


@router.post("/profile-summary/{lead_id}")
async def generate_profile_summary(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Generate an AI business profile summary from scraped data."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    detail_result = await db.execute(select(LeadDetail).where(LeadDetail.lead_id == lead_id))
    detail = detail_result.scalar_one_or_none()
    
    system_prompt = """You are creating a business profile summary to guide website mockup creation. Include:
1. What the business does (1-2 sentences)
2. Their key services/specialties
3. Their brand personality (based on reviews and description)
4. Target customer profile
5. Key selling points to highlight on their website

Keep it to 100-150 words. This will be used to auto-generate their website mockup."""
    
    user_msg = f"""Business: {lead.name}
Category: {lead.category}
Address: {lead.address}
Rating: {lead.rating} ({lead.review_count} reviews)
Phone: {lead.phone}
"""
    
    if detail:
        user_msg += f"""Description: {detail.description or 'N/A'}
Services: {json.dumps(detail.services) if detail.services else 'N/A'}
Hours: {json.dumps(detail.hours) if detail.hours else 'N/A'}
Top Reviews: {json.dumps(detail.top_reviews[:3]) if detail.top_reviews else 'N/A'}"""
    
    response = await call_openai(db, system_prompt, user_msg, max_tokens=400)
    
    # Save to lead details
    if detail:
        detail.ai_profile_summary = response
    
    return {"summary": response, "lead_id": lead_id}
