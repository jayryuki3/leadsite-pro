"""Mockups API routes - AI website mockup generation and editing."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models.lead import Lead, LeadDetail
from models.mockup import Mockup
from models.activity import Activity
from routes.settings import get_setting_value
from routes.ai import call_openai

router = APIRouter()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOCKUPS_DIR = os.path.join(BASE_DIR, "mockups")


class HtmlUpdate(BaseModel):
    html: str

class AiEditRequest(BaseModel):
    instruction: str


MOCKUP_SYSTEM_PROMPT = """You are an expert web designer. Generate a complete, production-ready single-page HTML website for a local business.

Requirements:
- Use Tailwind CSS via CDN: <script src="https://cdn.tailwindcss.com"></script>
- Fully responsive (mobile-first)
- Modern, clean, professional design
- Include these sections:
  1. Navigation bar with business name and phone
  2. Hero section with compelling headline, tagline, and CTA button
  3. About section (2-3 sentences)
  4. Services section (grid of cards)
  5. Testimonials section (2-3 real reviews if provided)
  6. Contact section with address, phone, hours, embedded Google Map placeholder
  7. Footer with social links and copyright
- Use appropriate icons (Heroicons via CDN or Unicode symbols)
- Color scheme: extract from brand colors if provided, otherwise choose a professional scheme matching the industry
- Include a "Book Now" or "Get a Quote" floating CTA button
- All placeholder images should use https://placehold.co/ with appropriate dimensions
- The HTML must be COMPLETE and SELF-CONTAINED (no external files except CDN links)
- Return ONLY the HTML code, no markdown fences, no explanations"""


@router.post("/generate/{lead_id}")
async def generate_mockup(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Generate an AI mockup website for a lead."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Get enriched details
    detail_result = await db.execute(select(LeadDetail).where(LeadDetail.lead_id == lead_id))
    detail = detail_result.scalar_one_or_none()
    
    # Build the prompt with business info
    biz_info = f"""Business Name: {lead.name}
Category: {lead.category.replace('_', ' ').title()}
Address: {lead.address}
Phone: {lead.phone or 'N/A'}
Rating: {lead.rating} stars ({lead.review_count} reviews)
Google Maps: {lead.google_maps_url or 'N/A'}
"""
    
    if detail:
        if detail.description:
            biz_info += f"\nDescription: {detail.description}"
        if detail.services:
            biz_info += f"\nServices: {json.dumps(detail.services)}"
        if detail.hours:
            biz_info += f"\nHours: {json.dumps(detail.hours)}"
        if detail.top_reviews:
            reviews_text = []
            for r in detail.top_reviews[:3]:
                reviews_text.append(f"- {r.get('user', 'Customer')}: \"{r.get('text', '')[:200]}\" ({r.get('rating', 5)} stars)")
            biz_info += f"\nTestimonials:\n" + "\n".join(reviews_text)
        if detail.brand_colors:
            biz_info += f"\nBrand Colors: {json.dumps(detail.brand_colors)}"
        if detail.ai_profile_summary:
            biz_info += f"\nAI Profile Summary: {detail.ai_profile_summary}"
    
    # Generate HTML via OpenAI
    html_content = await call_openai(
        db,
        MOCKUP_SYSTEM_PROMPT,
        f"Create a website for this business:\n\n{biz_info}",
        max_tokens=4000,
    )
    
    # Clean up response - remove markdown fences if present
    html_content = html_content.strip()
    if html_content.startswith("```html"):
        html_content = html_content[7:]
    if html_content.startswith("```"):
        html_content = html_content[3:]
    if html_content.endswith("```"):
        html_content = html_content[:-3]
    html_content = html_content.strip()
    
    # Save to file
    os.makedirs(MOCKUPS_DIR, exist_ok=True)
    safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in lead.name.lower())[:50]
    filename = f"{safe_name}_{lead_id}.html"
    filepath = os.path.join(MOCKUPS_DIR, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    # Check for existing mockup
    existing = await db.execute(select(Mockup).where(Mockup.lead_id == lead_id))
    mockup = existing.scalar_one_or_none()
    
    if mockup:
        mockup.html_path = f"mockups/{filename}"
        mockup.version += 1
        mockup.ai_prompt_used = biz_info[:2000]
    else:
        mockup = Mockup(
            lead_id=lead_id,
            html_path=f"mockups/{filename}",
            template_name="ai-generated",
            ai_prompt_used=biz_info[:2000],
            version=1,
        )
        db.add(mockup)
    
    if lead.status in ("new", "audited", "prospect"):
        lead.status = "mockup_created"
    
    activity = Activity(
        action="mockup_generated",
        description=f"Generated AI mockup for {lead.name}",
        lead_id=lead_id,
        metadata_json={"filename": filename, "version": mockup.version},
    )
    db.add(activity)
    
    await db.flush()
    
    return {
        "mockup_id": mockup.id,
        "lead_id": lead_id,
        "html_path": f"/static/mockups/{filename}",
        "version": mockup.version,
        "html_preview": html_content[:500] + "...",
    }


@router.get("/")
async def list_mockups(db: AsyncSession = Depends(get_db)):
    """List all mockups with lead info."""
    result = await db.execute(
        select(Mockup, Lead.name, Lead.category)
        .join(Lead, Lead.id == Mockup.lead_id)
        .order_by(Mockup.updated_at.desc())
    )
    rows = result.all()
    
    return {
        "mockups": [
            {
                "id": m.id,
                "lead_id": m.lead_id,
                "lead_name": name,
                "lead_category": category,
                "html_path": f"/static/{m.html_path}" if m.html_path else None,
                "screenshot_path": f"/static/{m.screenshot_path}" if m.screenshot_path else None,
                "version": m.version,
                "created_at": str(m.created_at) if m.created_at else None,
            }
            for m, name, category in rows
        ]
    }


@router.get("/{mockup_id}")
async def get_mockup(mockup_id: int, db: AsyncSession = Depends(get_db)):
    """Get mockup details including full HTML content."""
    result = await db.execute(select(Mockup).where(Mockup.id == mockup_id))
    mockup = result.scalar_one_or_none()
    if not mockup:
        raise HTTPException(status_code=404, detail="Mockup not found")
    
    # Read HTML content
    html_content = ""
    if mockup.html_path:
        full_path = os.path.join(BASE_DIR, mockup.html_path)
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                html_content = f.read()
    
    return {
        "id": mockup.id,
        "lead_id": mockup.lead_id,
        "html": html_content,
        "html_path": f"/static/{mockup.html_path}" if mockup.html_path else None,
        "screenshot_path": f"/static/{mockup.screenshot_path}" if mockup.screenshot_path else None,
        "version": mockup.version,
        "customizations": mockup.customizations,
    }


@router.put("/{mockup_id}")
async def update_mockup_html(mockup_id: int, data: HtmlUpdate, db: AsyncSession = Depends(get_db)):
    """Manually update mockup HTML."""
    result = await db.execute(select(Mockup).where(Mockup.id == mockup_id))
    mockup = result.scalar_one_or_none()
    if not mockup:
        raise HTTPException(status_code=404, detail="Mockup not found")
    
    if mockup.html_path:
        full_path = os.path.join(BASE_DIR, mockup.html_path)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(data.html)
    
    mockup.version += 1
    return {"success": True, "version": mockup.version}


@router.post("/{mockup_id}/ai-edit")
async def ai_edit_mockup(mockup_id: int, data: AiEditRequest, db: AsyncSession = Depends(get_db)):
    """Use AI to modify the mockup based on a natural language instruction."""
    result = await db.execute(select(Mockup).where(Mockup.id == mockup_id))
    mockup = result.scalar_one_or_none()
    if not mockup:
        raise HTTPException(status_code=404, detail="Mockup not found")
    
    # Read current HTML
    html_content = ""
    if mockup.html_path:
        full_path = os.path.join(BASE_DIR, mockup.html_path)
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                html_content = f.read()
    
    if not html_content:
        raise HTTPException(status_code=400, detail="No HTML content to edit")
    
    edit_prompt = f"""You are editing an existing HTML website. Apply the following change:

INSTRUCTION: {data.instruction}

Return the COMPLETE modified HTML. Do not explain, just return the full HTML code.
Do not add markdown fences."""
    
    modified_html = await call_openai(
        db,
        edit_prompt,
        f"Current HTML:\n\n{html_content}",
        max_tokens=4000,
    )
    
    # Clean up
    modified_html = modified_html.strip()
    if modified_html.startswith("```html"): modified_html = modified_html[7:]
    if modified_html.startswith("```"): modified_html = modified_html[3:]
    if modified_html.endswith("```"): modified_html = modified_html[:-3]
    modified_html = modified_html.strip()
    
    # Save
    if mockup.html_path:
        full_path = os.path.join(BASE_DIR, mockup.html_path)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(modified_html)
    
    mockup.version += 1
    
    return {
        "success": True,
        "html": modified_html,
        "version": mockup.version,
        "instruction_applied": data.instruction,
    }


@router.delete("/{mockup_id}")
async def delete_mockup(mockup_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a mockup."""
    from sqlalchemy import delete
    result = await db.execute(select(Mockup).where(Mockup.id == mockup_id))
    mockup = result.scalar_one_or_none()
    if not mockup:
        raise HTTPException(status_code=404, detail="Mockup not found")
    
    # Delete file
    if mockup.html_path:
        full_path = os.path.join(BASE_DIR, mockup.html_path)
        if os.path.exists(full_path):
            os.remove(full_path)
    
    await db.execute(delete(Mockup).where(Mockup.id == mockup_id))
    return {"success": True, "deleted": mockup_id}
