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


MOCKUP_SYSTEM_PROMPT = """You are an expert web designer. Generate a complete, production-ready MULTI-PAGE single-file HTML website for a local business.

The site must work as a single-file SPA with multiple navigable "pages" using JavaScript show/hide.

ARCHITECTURE:
- Use Tailwind CSS via CDN: <script src="https://cdn.tailwindcss.com"></script>
- Use Lucide Icons via CDN: <script src="https://unpkg.com/lucide@latest"></script> then call lucide.createIcons() after DOM loads
- Each "page" is a <section> with a unique id (e.g. id="page-home", id="page-about", id="page-services", id="page-contact")
- Only one page-section is visible at a time (display:block), the rest are hidden (display:none)
- Navigation links call a JS function showPage('page-home') that hides all page-sections and shows the target
- The FIRST page (Home) is visible by default on load

REQUIRED PAGES:
1. HOME - Hero section with compelling headline, tagline, and CTA button. Quick overview cards for services.
2. ABOUT - Business story, mission, team/owner info (2-3 paragraphs). Include an FAQ accordion (click to expand/collapse answers).
3. SERVICES - Grid of service cards with icons, descriptions, and pricing placeholders.
4. CONTACT - Address, phone, email, business hours, a contact form with JS validation (required fields, email format, show inline errors, show success toast on valid submit), and a Google Map placeholder iframe.

NAVIGATION:
- Sticky top nav bar with business name/logo on the left, page links in the center, and phone number on the right
- Mobile: hamburger menu button that toggles a slide-down mobile menu with the same page links
- Active page link should be visually highlighted (e.g. underline or color change)
- All nav links use onclick="showPage('page-xxx')" and also close the mobile menu if open

INTERACTIVE ELEMENTS:
- showPage() function scrolls to top of page when switching
- FAQ accordion on About page: clicking a question toggles its answer visibility
- Floating "Back to Top" button (appears on scroll, smooth scrolls to top)
- Contact form: inline validation on submit, success message displayed without page reload
- Hover effects on all cards and buttons (scale, shadow, or color transitions)
- Mobile hamburger menu open/close toggle

DESIGN:
- Fully responsive (mobile-first)
- Modern, clean, professional design
- Color scheme: extract from brand colors if provided, otherwise choose a professional palette matching the industry
- Use https://placehold.co/ for all placeholder images with appropriate dimensions
- Consistent spacing, typography, and border-radius throughout
- Footer on every page with business name, quick links, and copyright

OUTPUT RULES:
- The HTML must be COMPLETE and SELF-CONTAINED (no external files except CDN links)
- Include ALL JavaScript in a single <script> tag before </body>
- The script MUST include: showPage(), mobile menu toggle, FAQ accordion, form validation, back-to-top button logic
- Return ONLY raw HTML. No markdown fences, no explanations, no comments outside the HTML."""


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
    
    edit_prompt = f"""You are editing an existing multi-page single-file HTML website. Apply ONLY the requested change.

INSTRUCTION: {data.instruction}

CRITICAL RULES:
1. PRESERVE all existing page sections (page-home, page-about, page-services, page-contact, etc.) - do NOT remove or merge them
2. PRESERVE the showPage() navigation system, mobile hamburger menu toggle, FAQ accordion, form validation, and back-to-top logic
3. PRESERVE all existing JavaScript in the <script> tag - only add to it if the instruction requires new interactivity
4. Only modify the specific part the instruction asks about - leave everything else UNCHANGED
5. Return the COMPLETE HTML document including ALL pages and ALL scripts, even sections you did not change
6. Do not add markdown fences or explanations - return raw HTML only
7. If adding a new page section, also add its nav link to both desktop and mobile menus"""
    
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
