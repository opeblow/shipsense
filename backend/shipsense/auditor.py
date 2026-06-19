import asyncio
import json
import re
import httpx
from bs4 import BeautifulSoup

PAGESPEED_API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
PAGESPEED_TIMEOUT = 20
SCRAPE_TIMEOUT = 15

KNOWN_TRACKING_DOMAINS = {
    "googletagmanager.com", "google-analytics.com", "facebook.net",
    "fbcdn.net", "doubleclick.net", "adsrvr.org", "adnxs.com",
    "criteo.com", "criteo.net", "hotjar.com", "fullstory.com",
    "amplitude.com", "mixpanel.com", "segment.io", "segment.com",
    "hubspot.com", "linkedin.com/analytics", "snapchat.com",
    "tiktok.com", "twitter.com/analytics", "pinterest.com",
    "reddit.com/analytics", "quantserve.com", "scorecardresearch.com",
    "newrelic.com", "datadoghq.com", "sentry.io",
}

GUEST_KEYWORDS = [
    "guest", "without account", "continue without", "skip sign in",
    "checkout as guest", "order without account", "guest checkout",
]


def _parse_pagespeed(data: dict) -> dict:
    if not data:
        return {}
    audits = (data.get("lighthouseResult") or data)
    categories = audits.get("categories", {}) or {}

    def _score(key):
        c = categories.get(key)
        return round((c.get("score", 0) or 0) * 100) if c else None

    perf = _score("performance")
    a11y = _score("accessibility")
    seo = _score("seo")

    audits_map = audits.get("audits", {}) or {}
    lcp = audits_map.get("largest-contentful-paint", {}).get("numericValue")
    cls = audits_map.get("cumulative-layout-shift", {}).get("numericValue")
    tbt = audits_map.get("total-blocking-time", {}).get("numericValue")

    opportunities = []
    for key, audit in audits_map.items():
        if audit.get("details", {}).get("type") == "opportunity":
            savings = 0
            details = audit.get("details", {})
            if details.get("type") == "opportunity":
                items = details.get("items", [])
                if items:
                    savings = items[0].get("wastedMs", 0) or items[0].get("potentialSavingsMs", 0) or 0
            opportunities.append({
                "title": audit.get("title", key),
                "savings_ms": round(savings),
            })

    opportunities.sort(key=lambda x: x["savings_ms"], reverse=True)

    return {
        "performance_score": perf,
        "accessibility_score": a11y,
        "seo_score": seo,
        "core_web_vitals": {
            "lcp": f"{round(lcp / 1000, 1)}s" if lcp else None,
            "cls": round(cls, 2) if cls is not None else None,
            "tbt": f"{round(tbt)}ms" if tbt else None,
        },
        "pagespeed_opportunities": opportunities[:5],
    }


async def run_pagespeed_audit(url: str) -> dict:
    params = {
        "url": url,
        "category": ["performance", "accessibility", "seo", "best-practices"],
        "strategy": "mobile",
    }
    try:
        async with httpx.AsyncClient(timeout=PAGESPEED_TIMEOUT) as c:
            resp = await c.get(PAGESPEED_API, params=params)
            resp.raise_for_status()
            return _parse_pagespeed(resp.json())
    except Exception as e:
        return {"error": f"PageSpeed audit failed: {str(e)}"}


async def scrape_page(url: str) -> dict:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    try:
        async with httpx.AsyncClient(timeout=SCRAPE_TIMEOUT, follow_redirects=True) as c:
            resp = await c.get(url, headers=headers)
            resp.raise_for_status()
            html = resp.text
    except Exception as e:
        return {"error": f"Page scrape failed: {str(e)}"}

    soup = BeautifulSoup(html, "lxml")

    form_fields = len(soup.select("input, select, textarea"))

    body_text = soup.get_text(separator=" ", strip=True).lower()
    has_guest = any(kw in body_text for kw in GUEST_KEYWORDS)

    tracking_count = 0
    for script in soup.find_all("script", src=True):
        src = script["src"].lower()
        if any(d in src for d in KNOWN_TRACKING_DOMAINS):
            tracking_count += 1

    has_viewport = bool(soup.select_one("meta[name=viewport]"))
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    meta_desc = soup.select_one("meta[name=description]")
    meta_desc_content = meta_desc.get("content", "").strip() if meta_desc else None

    viewport_width = None
    viewport_meta = soup.select_one("meta[name=viewport]")
    if viewport_meta:
        content = viewport_meta.get("content", "")
        m = re.search(r'width\s*=\s*(\d+|device-width)', content)
        if m:
            viewport_width = m.group(1)

    above_fold_ctas = 0
    for tag in ("a", "button"):
        for el in soup.select(f"{tag}:not(nav {tag}):not(footer {tag})"):
            text = el.get_text(strip=True).lower()
            if any(kw in text for kw in ("sign up", "signup", "get started", "start free",
                                          "buy", "shop", "order", "subscribe", "try",
                                          "download", "install", "register", "join",
                                          "book now", "see pricing", "pricing")):
                above_fold_ctas += 1

    has_cookie_banner = bool(
        soup.find(string=re.compile(r"cookie|gdpr|ccpa|consent", re.I))
        or soup.select_one("[class*=cookie], [id*=cookie], [class*=consent], [id*=consent]")
    )
    has_popup = bool(
        soup.select_one("[class*=modal], [id*=modal], [class*=overlay], [id*=overlay], "
                        "[class*=popup], [id*=popup], [class*=lightbox], [id*=lightbox]")
    )
    autoplay_video = bool(
        soup.select_one("video[autoplay], video[data-autoplay]")
        or soup.select_one("[autoplay]")
    )

    return {
        "form_field_count": form_fields,
        "has_guest_checkout": has_guest,
        "tracking_script_count": tracking_count,
        "has_mobile_viewport": has_viewport,
        "page_title": title,
        "meta_description": bool(meta_desc_content),
        "ctas_above_fold": above_fold_ctas,
        "has_cookie_banner": has_cookie_banner,
        "has_popup": has_popup,
        "has_autoplay_video": autoplay_video,
    }


async def run_full_audit(url: str) -> dict:
    pagespeed_result, scrape_result = await asyncio.gather(
        run_pagespeed_audit(url),
        scrape_page(url),
    )

    result = {"url": url}

    if "error" in pagespeed_result:
        result["pagespeed_error"] = pagespeed_result["error"]
    else:
        result.update(pagespeed_result)

    if "error" in scrape_result:
        result["scrape_error"] = scrape_result["error"]
    else:
        result.update(scrape_result)

    return result
