"""Business info scraping service - extracts data from Google and Yelp."""
import httpx
from bs4 import BeautifulSoup
import re
import json
from typing import Optional, Dict, List, Any


async def scrape_yelp_business(business_name: str, location: str, yelp_api_key: Optional[str] = None) -> Dict[str, Any]:
    """Search and scrape business info from Yelp."""
    result = {
        "description": "",
        "services": [],
        "hours": {},
        "owner_name": "",
        "reviews": [],
        "photos": [],
        "yelp_url": "",
        "categories": [],
    }
    
    if yelp_api_key:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Search for the business
                search_resp = await client.get(
                    "https://api.yelp.com/v3/businesses/search",
                    headers={"Authorization": f"Bearer {yelp_api_key}"},
                    params={"term": business_name, "location": location, "limit": 1},
                )
                
                if search_resp.status_code == 200:
                    data = search_resp.json()
                    businesses = data.get("businesses", [])
                    
                    if businesses:
                        biz = businesses[0]
                        biz_id = biz.get("id", "")
                        result["yelp_url"] = biz.get("url", "")
                        result["categories"] = [c.get("title", "") for c in biz.get("categories", [])]
                        result["photos"] = biz.get("photos", [])
                        
                        # Get detailed info
                        detail_resp = await client.get(
                            f"https://api.yelp.com/v3/businesses/{biz_id}",
                            headers={"Authorization": f"Bearer {yelp_api_key}"},
                        )
                        
                        if detail_resp.status_code == 200:
                            detail = detail_resp.json()
                            result["photos"] = detail.get("photos", result["photos"])
                            
                            hours_data = detail.get("hours", [{}])
                            if hours_data:
                                open_hours = hours_data[0].get("open", [])
                                day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                                for h in open_hours:
                                    day = day_names[h.get("day", 0)]
                                    start = h.get("start", "")
                                    end = h.get("end", "")
                                    if start and end:
                                        result["hours"][day] = f"{start[:2]}:{start[2:]}-{end[:2]}:{end[2:]}"
                            
                            # Special hours / transactions as services
                            transactions = detail.get("transactions", [])
                            if transactions:
                                result["services"].extend([t.replace("_", " ").title() for t in transactions])
                        
                        # Get reviews
                        review_resp = await client.get(
                            f"https://api.yelp.com/v3/businesses/{biz_id}/reviews",
                            headers={"Authorization": f"Bearer {yelp_api_key}"},
                            params={"limit": 5, "sort_by": "yelp_sort"},
                        )
                        
                        if review_resp.status_code == 200:
                            reviews_data = review_resp.json().get("reviews", [])
                            for r in reviews_data:
                                result["reviews"].append({
                                    "text": r.get("text", ""),
                                    "rating": r.get("rating", 0),
                                    "user": r.get("user", {}).get("name", "Anonymous"),
                                    "time": r.get("time_created", ""),
                                })
        except Exception as e:
            print(f"Yelp API error: {e}")
    
    return result


async def scrape_website_content(url: str) -> Dict[str, Any]:
    """Scrape a business website for content, branding, and services."""
    result = {
        "description": "",
        "services": [],
        "brand_colors": [],
        "logo_url": "",
        "social_links": {},
    }
    
    if not url:
        return result
    
    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; LeadSitePro/1.0)"}
        ) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return result
            
            soup = BeautifulSoup(resp.text, "lxml")
            
            # Extract description from meta
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc:
                result["description"] = meta_desc.get("content", "").strip()
            
            # Extract logo
            logo = soup.find("img", class_=re.compile(r"logo", re.I))
            if not logo:
                logo = soup.find("img", attrs={"alt": re.compile(r"logo", re.I)})
            if logo and logo.get("src"):
                src = logo["src"]
                if src.startswith("/"):
                    from urllib.parse import urljoin
                    src = urljoin(url, src)
                result["logo_url"] = src
            
            # Extract colors from inline styles and CSS
            colors = set()
            style_tags = soup.find_all("style")
            all_styles = " ".join(s.string or "" for s in style_tags)
            hex_colors = re.findall(r"#([0-9a-fA-F]{3,6})\b", all_styles)
            for c in hex_colors[:10]:
                if len(c) in (3, 6) and c.lower() not in ("fff", "ffffff", "000", "000000", "333", "333333", "666", "666666", "999", "999999"):
                    colors.add(f"#{c}")
            result["brand_colors"] = list(colors)[:5]
            
            # Extract services from headings and lists
            services = []
            for heading in soup.find_all(["h2", "h3"]):
                text = heading.get_text(strip=True).lower()
                if any(kw in text for kw in ["service", "what we do", "our work", "specialt", "offering"]):
                    # Get the next sibling list or paragraph
                    next_el = heading.find_next_sibling()
                    if next_el and next_el.name == "ul":
                        for li in next_el.find_all("li"):
                            services.append(li.get_text(strip=True))
                    elif next_el and next_el.name == "p":
                        services.append(next_el.get_text(strip=True))
            result["services"] = services[:15]
            
            # Extract social links
            social_patterns = {
                "facebook": r"facebook\.com",
                "instagram": r"instagram\.com",
                "twitter": r"(twitter|x)\.com",
                "linkedin": r"linkedin\.com",
                "youtube": r"youtube\.com",
                "tiktok": r"tiktok\.com",
            }
            for a in soup.find_all("a", href=True):
                href = a["href"]
                for platform, pattern in social_patterns.items():
                    if re.search(pattern, href) and platform not in result["social_links"]:
                        result["social_links"][platform] = href
            
    except Exception as e:
        print(f"Website scrape error: {e}")
    
    return result


async def enrich_lead(lead_name: str, lead_address: str, lead_website: str, yelp_api_key: Optional[str] = None) -> Dict[str, Any]:
    """Full enrichment: combine Yelp + website scraping."""
    # Run both in parallel
    import asyncio
    yelp_task = scrape_yelp_business(lead_name, lead_address, yelp_api_key)
    web_task = scrape_website_content(lead_website)
    
    yelp_data, web_data = await asyncio.gather(yelp_task, web_task)
    
    # Merge results
    description = web_data.get("description") or yelp_data.get("description") or ""
    services = list(set(web_data.get("services", []) + yelp_data.get("services", [])))
    
    return {
        "description": description,
        "services": services,
        "hours": yelp_data.get("hours", {}),
        "owner_name": yelp_data.get("owner_name", ""),
        "top_reviews": yelp_data.get("reviews", []),
        "photos": yelp_data.get("photos", []),
        "brand_colors": web_data.get("brand_colors", []),
        "logo_url": web_data.get("logo_url", ""),
        "social_links": web_data.get("social_links", {}),
        "yelp_url": yelp_data.get("yelp_url", ""),
        "yelp_categories": yelp_data.get("categories", []),
    }
