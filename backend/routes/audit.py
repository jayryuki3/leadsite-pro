"""Audit API routes - website quality scoring for leads."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
from bs4 import BeautifulSoup
import json
import re
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models.lead import Lead
from models.activity import Activity

router = APIRouter()


async def audit_website(url: str) -> dict:
    """Audit a single website and return quality metrics."""
    if not url:
        return {
            "score": 0,
            "has_website": False,
            "details": {"reason": "No website found"},
        }
    
    metrics = {
        "has_website": True,
        "is_https": False,
        "has_viewport_meta": False,
        "has_meta_description": False,
        "has_title": False,
        "has_h1": False,
        "has_alt_tags": False,
        "has_structured_data": False,
        "has_social_links": False,
        "page_size_kb": 0,
        "last_modified": None,
        "tech_detected": [],
        "missing_elements": [],
        "score_breakdown": {},
    }
    
    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; LeadSitePro/1.0; website audit)"}
        ) as client:
            resp = await client.get(url)
            
            # HTTPS check
            metrics["is_https"] = str(resp.url).startswith("https")
            
            # Last modified header
            metrics["last_modified"] = resp.headers.get("last-modified", None)
            
            # Page size
            content = resp.text
            metrics["page_size_kb"] = round(len(content.encode()) / 1024, 1)
            
            soup = BeautifulSoup(content, "lxml")
            
            # Viewport meta (mobile responsiveness)
            viewport = soup.find("meta", attrs={"name": "viewport"})
            metrics["has_viewport_meta"] = viewport is not None
            
            # Meta description
            meta_desc = soup.find("meta", attrs={"name": "description"})
            metrics["has_meta_description"] = meta_desc is not None and bool(meta_desc.get("content", "").strip())
            
            # Title tag
            title = soup.find("title")
            metrics["has_title"] = title is not None and bool(title.string and title.string.strip())
            metrics["title_text"] = title.string.strip() if title and title.string else ""
            
            # H1 tag
            h1 = soup.find("h1")
            metrics["has_h1"] = h1 is not None
            
            # Image alt tags
            images = soup.find_all("img")
            if images:
                imgs_with_alt = sum(1 for img in images if img.get("alt", "").strip())
                metrics["has_alt_tags"] = imgs_with_alt / len(images) > 0.5
                metrics["alt_tag_ratio"] = f"{imgs_with_alt}/{len(images)}"
            else:
                metrics["has_alt_tags"] = True  # No images = not penalized
            
            # Structured data (JSON-LD)
            json_ld = soup.find_all("script", attrs={"type": "application/ld+json"})
            metrics["has_structured_data"] = len(json_ld) > 0
            
            # Social media links
            social_domains = ["facebook.com", "instagram.com", "twitter.com", "x.com", "linkedin.com", "youtube.com", "tiktok.com", "yelp.com"]
            all_links = [a.get("href", "") for a in soup.find_all("a", href=True)]
            social_found = [d for d in social_domains if any(d in link for link in all_links)]
            metrics["has_social_links"] = len(social_found) > 0
            metrics["social_platforms"] = social_found
            
            # Tech detection
            tech = []
            if "wp-content" in content or "wordpress" in content.lower():
                tech.append("WordPress")
            if "wix.com" in content:
                tech.append("Wix")
            if "squarespace" in content.lower():
                tech.append("Squarespace")
            if "shopify" in content.lower():
                tech.append("Shopify")
            if "godaddy" in content.lower():
                tech.append("GoDaddy")
            if "weebly" in content.lower():
                tech.append("Weebly")
            if "bootstrap" in content.lower():
                tech.append("Bootstrap")
            if "tailwind" in content.lower():
                tech.append("Tailwind")
            if "react" in content.lower():
                tech.append("React")
            metrics["tech_detected"] = tech
            
            # Calculate score (0-100)
            score = 0
            breakdown = {}
            
            # HTTPS (15 points)
            pts = 15 if metrics["is_https"] else 0
            score += pts
            breakdown["https"] = pts
            
            # Mobile responsive (20 points)
            pts = 20 if metrics["has_viewport_meta"] else 0
            score += pts
            breakdown["mobile"] = pts
            
            # SEO basics (25 points total)
            seo = 0
            if metrics["has_title"]: seo += 8
            if metrics["has_meta_description"]: seo += 8
            if metrics["has_h1"]: seo += 5
            if metrics["has_alt_tags"]: seo += 4
            score += seo
            breakdown["seo"] = seo
            
            # Structured data (10 points)
            pts = 10 if metrics["has_structured_data"] else 0
            score += pts
            breakdown["structured_data"] = pts
            
            # Social presence (10 points)
            pts = min(len(social_found) * 3, 10)
            score += pts
            breakdown["social"] = pts
            
            # Page size penalty (10 points - penalize very large or tiny pages)
            if 5 < metrics["page_size_kb"] < 3000:
                pts = 10
            elif metrics["page_size_kb"] <= 5:
                pts = 3  # Suspiciously small
            else:
                pts = 5  # Too large
            score += pts
            breakdown["page_size"] = pts
            
            # Content quality (10 points)
            text_content = soup.get_text(separator=" ", strip=True)
            word_count = len(text_content.split())
            if word_count > 200:
                pts = 10
            elif word_count > 50:
                pts = 5
            else:
                pts = 2
            score += pts
            breakdown["content"] = pts
            
            metrics["score_breakdown"] = breakdown
            metrics["word_count"] = word_count
            
            # Track missing elements
            if not metrics["is_https"]: metrics["missing_elements"].append("HTTPS")
            if not metrics["has_viewport_meta"]: metrics["missing_elements"].append("Mobile viewport")
            if not metrics["has_meta_description"]: metrics["missing_elements"].append("Meta description")
            if not metrics["has_title"]: metrics["missing_elements"].append("Title tag")
            if not metrics["has_h1"]: metrics["missing_elements"].append("H1 heading")
            if not metrics["has_alt_tags"]: metrics["missing_elements"].append("Image alt tags")
            if not metrics["has_structured_data"]: metrics["missing_elements"].append("Structured data")
            if not metrics["has_social_links"]: metrics["missing_elements"].append("Social media links")
            
            return {"score": min(score, 100), "has_website": True, "details": metrics}
            
    except httpx.TimeoutException:
        return {"score": 10, "has_website": True, "details": {**metrics, "error": "Website timed out (>15s) - likely very slow"}}
    except httpx.ConnectError:
        return {"score": 5, "has_website": True, "details": {**metrics, "error": "Could not connect - site may be down"}}
    except Exception as e:
        return {"score": 5, "has_website": True, "details": {**metrics, "error": str(e)}}


@router.post("/batch")
async def audit_batch(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Audit unaudited leads in batch."""
    result = await db.execute(
        select(Lead)
        .where(Lead.website_quality_score == -1)
        .limit(limit)
    )
    leads = result.scalars().all()
    
    if not leads:
        return {"audited": 0, "message": "No unaudited leads found"}
    
    results = []
    for lead in leads:
        audit_result = await audit_website(lead.website)
        lead.website_quality_score = audit_result["score"]
        lead.audit_details = audit_result["details"]
        if lead.status == "new":
            lead.status = "audited"
        results.append({
            "lead_id": lead.id,
            "name": lead.name,
            "score": audit_result["score"],
        })
    
    activity = Activity(
        action="batch_audit_completed",
        description=f"Audited {len(results)} websites",
        metadata_json={"count": len(results), "avg_score": round(sum(r['score'] for r in results) / len(results), 1)},
    )
    db.add(activity)
    
    return {"audited": len(results), "results": results}


@router.get("/summary")
async def audit_summary(db: AsyncSession = Depends(get_db)):
    """Get audit summary statistics."""
    from sqlalchemy import func as sqlfunc
    
    total = await db.execute(select(sqlfunc.count(Lead.id)))
    audited = await db.execute(select(sqlfunc.count(Lead.id)).where(Lead.website_quality_score >= 0))
    no_website = await db.execute(select(sqlfunc.count(Lead.id)).where(Lead.website_quality_score == 0))
    avg_score = await db.execute(select(sqlfunc.avg(Lead.website_quality_score)).where(Lead.website_quality_score > 0))
    
    return {
        "total_leads": total.scalar(),
        "audited": audited.scalar(),
        "no_website": no_website.scalar(),
        "average_score": round(avg_score.scalar() or 0, 1),
    }


# ── Single Lead Audit (catch-all — MUST be last to avoid shadowing /batch and /summary) ─

@router.post("/{lead_id}")
async def audit_single_lead(lead_id: int, db: AsyncSession = Depends(get_db)):
    """Audit a single lead's website."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    audit_result = await audit_website(lead.website)
    
    lead.website_quality_score = audit_result["score"]
    lead.audit_details = audit_result["details"]
    lead.status = "audited" if lead.status == "new" else lead.status
    
    return {
        "lead_id": lead_id,
        "name": lead.name,
        "website": lead.website,
        "score": audit_result["score"],
        "has_website": audit_result["has_website"],
        "details": audit_result["details"],
    }