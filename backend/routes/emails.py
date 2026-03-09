"""Email API routes - AI outreach email drafting and sending."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel
from typing import Optional, List
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models.lead import Lead, LeadDetail
from models.mockup import Mockup
from models.email_draft import EmailDraft
from models.activity import Activity
from routes.settings import get_setting_value
from routes.ai import call_openai

router = APIRouter()


class GenerateEmailRequest(BaseModel):
    tone: str = "professional"  # professional, casual, friendly

class BatchGenerateRequest(BaseModel):
    lead_ids: List[int]
    tone: str = "professional"

class EmailUpdateRequest(BaseModel):
    subject: Optional[str] = None
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    recipient_email: Optional[str] = None


EMAIL_SYSTEM_PROMPT = """You are writing a cold outreach email from a web designer to a local business owner. The email should:

1. Be personalized with their business name and specific details
2. Open with a hook about their online presence (missing website, outdated site, etc.)
3. Mention that you've created a FREE preview/mockup of what their new site could look like
4. Include the pricing tiers as a clean, formatted section
5. End with a clear CTA to schedule a free 15-minute call
6. Be concise - max 250 words
7. Sound human, not salesy

Return a JSON object with exactly these fields:
{"subject": "email subject line", "body_html": "full HTML email body", "body_text": "plain text version"}

For body_html, use inline CSS for email compatibility. Use a clean layout with:
- A brief personal intro
- The mockup mention
- A pricing table with the tiers
- A CTA button (styled as a link)
- Professional signature

Return ONLY the JSON object, no markdown fences."""


@router.post("/generate/{lead_id}")
async def generate_email(lead_id: int, req: GenerateEmailRequest, db: AsyncSession = Depends(get_db)):
    """Generate a personalized outreach email for a lead."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Get enriched details
    detail_result = await db.execute(select(LeadDetail).where(LeadDetail.lead_id == lead_id))
    detail = detail_result.scalar_one_or_none()
    
    # Get mockup info
    mockup_result = await db.execute(select(Mockup).where(Mockup.lead_id == lead_id))
    mockup = mockup_result.scalar_one_or_none()
    
    # Get pricing tiers
    pricing_raw = await get_setting_value(db, "pricing_tiers")
    try:
        pricing = json.loads(pricing_raw) if pricing_raw else []
    except Exception:
        pricing = []
    
    # Get business info for signature
    biz_name = await get_setting_value(db, "business_name") or "Your Web Design Partner"
    biz_email = await get_setting_value(db, "business_email") or ""
    biz_phone = await get_setting_value(db, "business_phone") or ""
    calendly = await get_setting_value(db, "calendly_link") or ""
    
    # Build prompt context
    user_msg = f"""Tone: {req.tone}

Target Business:
- Name: {lead.name}
- Category: {lead.category.replace('_', ' ').title()}
- Rating: {lead.rating} stars ({lead.review_count} reviews)
- Website: {lead.website or 'NONE - they have no website!'}
- Website Quality Score: {lead.website_quality_score}/100
- Address: {lead.address}
"""
    
    if detail:
        if detail.owner_name:
            user_msg += f"- Owner/Contact: {detail.owner_name}\n"
        if detail.description:
            user_msg += f"- Business Description: {detail.description[:200]}\n"
    
    if mockup:
        user_msg += f"\nMockup: Yes, a preview website has been created for them.\n"
    
    # Format pricing for the prompt
    if pricing:
        user_msg += "\nPricing Tiers:\n"
        for tier in pricing:
            price_str = f"${tier['price']}"
            if tier.get('price_type') == 'monthly':
                price_str += "/mo (12-month contract)"
            user_msg += f"- {tier['display_name']}: {price_str} - {tier['description']}\n"
            for feat in tier.get('features', [])[:4]:
                user_msg += f"  * {feat}\n"
    
    user_msg += f"""\nYour Signature Info:
- Your Business: {biz_name}
- Email: {biz_email}
- Phone: {biz_phone}
- Booking Link: {calendly or 'your-booking-link.com'}
"""
    
    response = await call_openai(db, EMAIL_SYSTEM_PROMPT, user_msg, max_tokens=2000)
    
    # Parse JSON response
    try:
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            email_data = json.loads(json_match.group())
        else:
            email_data = {"subject": f"A new website for {lead.name}", "body_html": response, "body_text": response}
    except Exception:
        email_data = {"subject": f"A new website for {lead.name}", "body_html": response, "body_text": response}
    
    # Save draft
    draft = EmailDraft(
        lead_id=lead_id,
        mockup_id=mockup.id if mockup else None,
        subject=email_data.get("subject", ""),
        body_html=email_data.get("body_html", ""),
        body_text=email_data.get("body_text", ""),
        tone=req.tone,
        pricing_tier_shown="all",
        status="draft",
    )
    db.add(draft)
    
    activity = Activity(
        action="email_drafted",
        description=f"Drafted outreach email for {lead.name}",
        lead_id=lead_id,
    )
    db.add(activity)
    
    await db.flush()
    
    return {
        "draft_id": draft.id,
        "lead_id": lead_id,
        "subject": draft.subject,
        "body_html": draft.body_html,
        "body_text": draft.body_text,
        "tone": draft.tone,
    }


@router.post("/batch-generate")
async def batch_generate(req: BatchGenerateRequest, db: AsyncSession = Depends(get_db)):
    """Generate emails for multiple leads."""
    results = []
    for lead_id in req.lead_ids:
        try:
            single_req = GenerateEmailRequest(tone=req.tone)
            result = await generate_email(lead_id, single_req, db)
            results.append({"lead_id": lead_id, "success": True, "draft_id": result["draft_id"]})
        except Exception as e:
            results.append({"lead_id": lead_id, "success": False, "error": str(e)})
    
    return {"generated": len([r for r in results if r["success"]]), "results": results}


@router.get("/")
async def list_drafts(db: AsyncSession = Depends(get_db)):
    """List all email drafts."""
    result = await db.execute(
        select(EmailDraft, Lead.name, Lead.category)
        .join(Lead, Lead.id == EmailDraft.lead_id)
        .order_by(EmailDraft.created_at.desc())
    )
    rows = result.all()
    
    return {
        "drafts": [
            {
                "id": d.id,
                "lead_id": d.lead_id,
                "lead_name": name,
                "lead_category": category,
                "subject": d.subject,
                "recipient_email": d.recipient_email,
                "tone": d.tone,
                "status": d.status,
                "created_at": str(d.created_at) if d.created_at else None,
                "sent_at": str(d.sent_at) if d.sent_at else None,
            }
            for d, name, category in rows
        ]
    }


@router.get("/{draft_id}")
async def get_draft(draft_id: int, db: AsyncSession = Depends(get_db)):
    """Get full email draft details."""
    result = await db.execute(select(EmailDraft).where(EmailDraft.id == draft_id))
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    return {
        "id": draft.id,
        "lead_id": draft.lead_id,
        "subject": draft.subject,
        "body_html": draft.body_html,
        "body_text": draft.body_text,
        "recipient_email": draft.recipient_email,
        "tone": draft.tone,
        "status": draft.status,
    }


@router.put("/{draft_id}")
async def update_draft(draft_id: int, data: EmailUpdateRequest, db: AsyncSession = Depends(get_db)):
    """Update an email draft."""
    result = await db.execute(select(EmailDraft).where(EmailDraft.id == draft_id))
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    if data.subject is not None: draft.subject = data.subject
    if data.body_html is not None: draft.body_html = data.body_html
    if data.body_text is not None: draft.body_text = data.body_text
    if data.recipient_email is not None: draft.recipient_email = data.recipient_email
    
    return {"success": True, "id": draft_id}


@router.post("/{draft_id}/send")
async def send_email(draft_id: int, db: AsyncSession = Depends(get_db)):
    """Send an email draft via SMTP."""
    result = await db.execute(select(EmailDraft).where(EmailDraft.id == draft_id))
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    if not draft.recipient_email:
        raise HTTPException(status_code=400, detail="Recipient email not set")
    
    # Get SMTP settings
    smtp_host = await get_setting_value(db, "smtp_host")
    smtp_port = int(await get_setting_value(db, "smtp_port") or "587")
    smtp_user = await get_setting_value(db, "smtp_username")
    smtp_pass = await get_setting_value(db, "smtp_password")
    from_name = await get_setting_value(db, "smtp_from_name") or "LeadSite Pro"
    from_email = await get_setting_value(db, "smtp_from_email") or smtp_user
    
    if not all([smtp_host, smtp_user, smtp_pass]):
        raise HTTPException(status_code=400, detail="SMTP not configured. Go to Settings.")
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = draft.subject
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = draft.recipient_email
        
        if draft.body_text:
            msg.attach(MIMEText(draft.body_text, "plain"))
        if draft.body_html:
            msg.attach(MIMEText(draft.body_html, "html"))
        
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        
        from datetime import datetime
        draft.status = "sent"
        draft.sent_at = datetime.utcnow()
        
        # Update lead status
        lead_result = await db.execute(select(Lead).where(Lead.id == draft.lead_id))
        lead = lead_result.scalar_one_or_none()
        if lead and lead.status in ("new", "audited", "prospect", "mockup_created"):
            lead.status = "contacted"
        
        activity = Activity(
            action="email_sent",
            description=f"Sent outreach email to {draft.recipient_email}",
            lead_id=draft.lead_id,
        )
        db.add(activity)
        
        return {"success": True, "sent_to": draft.recipient_email}
    
    except Exception as e:
        draft.status = "bounced"
        raise HTTPException(status_code=500, detail=f"Send failed: {str(e)}")


@router.delete("/{draft_id}")
async def delete_draft(draft_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an email draft."""
    result = await db.execute(delete(EmailDraft).where(EmailDraft.id == draft_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"success": True, "deleted": draft_id}
