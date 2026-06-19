import asyncio
import json
import re
import urllib.parse
import httpx
from bs4 import BeautifulSoup

PAGESPEED_API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
PAGESPEED_TIMEOUT = 25
SCRAPE_TIMEOUT = 20
HEADERS_TIMEOUT = 10

KNOWN_TRACKING_DOMAINS = {
    "googletagmanager.com", "google-analytics.com", "facebook.net",
    "fbcdn.net", "doubleclick.net", "adsrvr.org", "adnxs.com",
    "criteo.com", "criteo.net", "hotjar.com", "fullstory.com",
    "amplitude.com", "mixpanel.com", "segment.io", "segment.com",
    "hubspot.com", "linkedin.com", "snapchat.com",
    "tiktok.com", "pinterest.com",
    "redditstatic.com", "quantserve.com", "scorecardresearch.com",
    "newrelic.com", "datadoghq.com", "sentry.io", "cookiebot.com",
    "onetrust.com", "consentmanager.net", "cmp.usercentrics.eu",
}

GUEST_KEYWORDS = [
    "guest", "without account", "continue without", "skip sign in",
    "checkout as guest", "order without account", "guest checkout",
    "continue as guest",
]

CTA_KEYWORDS = [
    "sign up", "signup", "get started", "start free", "start now",
    "buy", "shop", "order", "subscribe", "try free", "try now",
    "download", "install", "register", "join", "join now",
    "book now", "see pricing", "pricing", "start trial", "free trial",
    "create account", "get early access", "request demo", "get demo",
    "talk to sales", "contact sales", "get access",
]


# ── PageSpeed ──────────────────────────────────────────────────────────────

def _parse_pagespeed(data: dict) -> dict:
    if not data:
        return {}
    audits = data.get("lighthouseResult") or data
    categories = audits.get("categories", {}) or {}

    def _score(key):
        c = categories.get(key)
        return round((c.get("score", 0) or 0) * 100) if c else None

    audits_map = audits.get("audits", {}) or {}
    lcp = audits_map.get("largest-contentful-paint", {}).get("numericValue")
    cls_val = audits_map.get("cumulative-layout-shift", {}).get("numericValue")
    tbt = audits_map.get("total-blocking-time", {}).get("numericValue")
    si = audits_map.get("speed-index", {}).get("numericValue")
    fcp = audits_map.get("first-contentful-paint", {}).get("numericValue")

    opportunities = []
    for key, audit in audits_map.items():
        if audit.get("details", {}).get("type") == "opportunity":
            items = audit.get("details", {}).get("items", [])
            savings = items[0].get("wastedMs", 0) or items[0].get("potentialSavingsMs", 0) or 0 if items else 0
            opportunities.append({
                "title": audit.get("title", key),
                "savings_ms": round(savings),
            })
    opportunities.sort(key=lambda x: x["savings_ms"], reverse=True)

    diag_list = []
    for key, audit in audits_map.items():
        if audit.get("details", {}).get("type") == "diagnostic" and audit.get("score") is not None and audit["score"] < 1:
            diag_list.append({
                "title": audit.get("title", key),
                "score": round(audit["score"] * 100),
            })
    diag_list.sort(key=lambda x: x["score"])

    return {
        "performance_score": _score("performance"),
        "accessibility_score": _score("accessibility"),
        "seo_score": _score("seo"),
        "best_practices_score": _score("best-practices"),
        "core_web_vitals": {
            "lcp": f"{round(lcp / 1000, 1)}s" if lcp else None,
            "cls": round(cls_val, 2) if cls_val is not None else None,
            "tbt": f"{round(tbt)}ms" if tbt else None,
            "fcp": f"{round(fcp / 1000, 1)}s" if fcp else None,
            "speed_index": f"{round(si / 1000, 1)}s" if si else None,
        },
        "pagespeed_opportunities": opportunities[:8],
        "pagespeed_diagnostics": diag_list[:5],
    }


async def _try_pagespeed(url: str, strategy: str, client: httpx.AsyncClient) -> dict | None:
    params = {
        "url": url,
        "category": ["performance", "accessibility", "seo", "best-practices"],
        "strategy": strategy,
    }
    resp = await client.get(PAGESPEED_API, params=params)
    if resp.status_code == 429:
        return None
    resp.raise_for_status()
    return _parse_pagespeed(resp.json())


async def run_pagespeed_audit(url: str) -> dict:
    retries = [0, 2, 4]
    strategies = ["mobile", "desktop"]
    last_error = None

    async with httpx.AsyncClient(timeout=PAGESPEED_TIMEOUT) as c:
        for strategy in strategies:
            for wait in retries:
                if wait:
                    await asyncio.sleep(wait)
                try:
                    result = await _try_pagespeed(url, strategy, c)
                    if result is not None:
                        result["strategy_used"] = strategy
                        return result
                    last_error = "Rate limited (429) on all retries"
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        last_error = f"Rate limited on {strategy}"
                        continue
                    last_error = f"HTTP {e.response.status_code} on {strategy}"
                    break
                except Exception as e:
                    last_error = f"{str(e)} on {strategy}"
                    break

    return {"error": last_error or "PageSpeed unavailable"}


# ── Response Headers ───────────────────────────────────────────────────────

async def analyze_headers(url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=HEADERS_TIMEOUT, follow_redirects=True) as c:
            resp = await c.head(url)
            h = resp.headers
    except Exception:
        try:
            async with httpx.AsyncClient(timeout=HEADERS_TIMEOUT, follow_redirects=True) as c:
                resp = await c.get(url)
                h = resp.headers
        except Exception as e:
            return {"header_analysis_error": str(e)}

    security = {
        "has_hsts": "strict-transport-security" in h,
        "has_csp": "content-security-policy" in h,
        "has_xframe": "x-frame-options" in h,
        "has_xcontent": "x-content-type-options" in h,
        "has_referrer_policy": "referrer-policy" in h,
        "has_permissions_policy": "permissions-policy" in h,
    }
    security["security_score"] = round(sum(1 for v in security.values() if v) / 6 * 100)

    cache_control = h.get("cache-control", "")
    return {
        "security_headers": security,
        "content_encoding": h.get("content-encoding"),
        "cache_control": cache_control,
        "has_compression": "content-encoding" in h,
        "content_type": h.get("content-type"),
        "server": h.get("server", h.get("via", "")),
        "redirect_count": len(resp.history) if hasattr(resp, "history") and resp.history else 0,
        "final_status": resp.status_code,
    }


# ── HTML Scrape ────────────────────────────────────────────────────────────

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
    body_text = soup.get_text(separator=" ", strip=True)
    body_lower = body_text.lower()
    word_count = len(body_text.split())

    # ── Forms ──
    forms = soup.find_all("form")
    form_inputs = soup.select("input, select, textarea")
    password_fields = len(soup.select("input[type=password]"))
    email_fields = len(soup.select("input[type=email]"))
    submit_buttons = len(soup.select("button[type=submit], input[type=submit]"))

    # ── Guest checkout ──
    has_guest = any(kw in body_lower for kw in GUEST_KEYWORDS)

    # ── Tracking ──
    tracking_count = 0
    tracking_details = []
    for script in soup.find_all("script", src=True):
        src = script["src"].lower()
        for domain in KNOWN_TRACKING_DOMAINS:
            if domain in src:
                tracking_count += 1
                tracking_details.append(domain.split(".")[0])
                break

    # ── Mobile / Viewport ──
    viewport_meta = soup.select_one("meta[name=viewport]")
    has_viewport = bool(viewport_meta)
    viewport_width = None
    if viewport_meta:
        m = re.search(r'width\s*=\s*(\d+|device-width)', viewport_meta.get("content", ""))
        if m:
            viewport_width = m.group(1)

    # ── SEO basics ──
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    title_length = len(title) if title else 0
    meta_desc = soup.select_one("meta[name=description]")
    meta_desc_content = meta_desc.get("content", "").strip() if meta_desc else None
    meta_desc_length = len(meta_desc_content) if meta_desc_content else 0
    canonical = soup.select_one("link[rel=canonical]")
    canonical_href = canonical.get("href") if canonical else None
    hreflang_tags = len(soup.select("link[rel=alternate][hreflang]"))
    has_robots = bool(soup.select_one("meta[name=robots]"))
    og_tags = len(soup.find_all("meta", property=re.compile(r"^og:")))
    twitter_tags = len(soup.find_all("meta", attrs={"name": re.compile(r"^twitter:")}))
    has_json_ld = bool(soup.select_one("script[type=application/ld+json]"))

    # ── Headings ──
    h1_tags = soup.find_all("h1")
    h1_count = len(h1_tags)
    h2_count = len(soup.find_all("h2"))
    heading_issues = []
    if h1_count == 0:
        heading_issues.append("Missing H1 tag")
    elif h1_count > 1:
        heading_issues.append(f"Multiple H1 tags ({h1_count})")

    # ── Images ──
    images = soup.find_all("img")
    total_images = len(images)
    images_no_alt = sum(1 for img in images if not img.get("alt"))
    images_no_dimensions = sum(1 for img in images if not img.get("width") or not img.get("height"))
    lazy_images = sum(1 for img in images if img.get("loading") == "lazy")

    # ── Links ──
    links = soup.find_all("a", href=True)
    internal_links = 0
    external_links = 0
    broken_href = 0
    parsed_url = urllib.parse.urlparse(url)
    base_domain = parsed_url.netloc
    for a in links:
        href = a["href"]
        if href.startswith("#") or href.startswith("javascript:"):
            broken_href += 1
            continue
        if href.startswith("http"):
            if base_domain in href:
                internal_links += 1
            else:
                external_links += 1
        else:
            internal_links += 1

    # ── Performance from HTML ──
    render_blocking = []
    for s in soup.find_all("script", src=True):
        if not s.get("async") and not s.get("defer"):
            render_blocking.append(f"script:{s['src'][:80]}")
    for l in soup.find_all("link", rel="stylesheet", href=True):
        render_blocking.append(f"css:{l['href'][:80]}")
    preconnect_hints = len(soup.select("link[rel=preconnect], link[rel=dns-prefetch]"))
    preload_hints = len(soup.select("link[rel=preload]"))
    font_links = soup.select("link[href*=fonts]")
    has_web_fonts = bool(font_links)
    has_font_display = False
    for style in soup.find_all("style"):
        if "@font-face" in style.get_text() and "font-display" in style.get_text():
            has_font_display = True
            break
    for link in font_links:
        css_text = ""
        if link.get("as") == "style" or link.get("rel") == ["stylesheet"]:
            has_web_fonts = True

    # ── CTAs ──
    cta_count = 0
    for tag in ("a", "button"):
        for el in soup.select(f"{tag}:not(nav {tag}):not(footer {tag})"):
            text = el.get_text(strip=True).lower()
            if any(kw in text for kw in CTA_KEYWORDS):
                cta_count += 1

    # ── Content elements ──
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
    has_hamburger_menu = bool(
        soup.select_one("[class*=hamburger], [id*=hamburger], "
                        "[class*=menu-toggle], [id*=menu-toggle]")
    )
    has_search = bool(
        soup.select_one("input[type=search], form[role=search], "
                        "[class*=search], [id*=search]")
    )
    has_footer = bool(soup.find("footer"))
    has_nav = bool(soup.find("nav"))

    # ── Accessibility ──
    aria_landmarks = len(soup.select("[role=banner], [role=main], [role=navigation], "
                                      "[role=complementary], [role=contentinfo], "
                                      "[role=form], [role=search]"))
    aria_labels = len(soup.select("[aria-label], [aria-labelledby]"))
    skip_link = bool(soup.select_one("a[href^=#main], a[href^=#content], a[href^=#skip]"))

    # ── Resource sizes ──
    inline_scripts = len(soup.find_all("script", string=True))
    inline_styles = len(soup.find_all("style", string=True))
    external_scripts = len(soup.find_all("script", src=True))
    external_styles = len(soup.find_all("link", rel="stylesheet"))

    # ── Frameworks (basic detection) ──
    frameworks = []
    if soup.select_one("[class*=react], [data-reactroot], #root, #___gatsby"):
        frameworks.append("React")
    if soup.select_one("[ng-version], [ng-app], [ng-controller]"):
        frameworks.append("Angular")
    if soup.select_one("[v-cloak], [v-bind], [v-model], #app, [x-data]"):
        frameworks.append("Vue/Svelte/Alpine")
    if soup.select("script[src*=next]") or soup.select_one("[data-nextjs]"):
        frameworks.append("Next.js")
    if soup.select_one("[class*=tailwind]"):
        frameworks.append("Tailwind")
    if "wordpress" in body_lower:
        frameworks.append("WordPress")
    if soup.select_one("link[href*=bootstrap], [class*=bootstrap]") or "bootstrap" in body_lower:
        frameworks.append("Bootstrap")

    return {
        # Forms & conversion
        "form_field_count": form_inputs,
        "form_count": len(forms),
        "has_password_field": password_fields > 0,
        "has_email_field": email_fields > 0,
        "submit_button_count": submit_buttons,
        "has_guest_checkout": has_guest,

        # Tracking
        "tracking_script_count": tracking_count,
        "tracking_tools": list(set(tracking_details))[:8],

        # Mobile
        "has_mobile_viewport": has_viewport,
        "viewport_width": viewport_width,

        # SEO
        "page_title": title,
        "title_length": title_length,
        "meta_description": bool(meta_desc_content),
        "meta_description_length": meta_desc_length,
        "has_canonical": bool(canonical_href),
        "has_hreflang": hreflang_tags > 0,
        "has_robots_meta": has_robots,
        "og_tag_count": og_tags,
        "twitter_tag_count": twitter_tags,
        "has_json_ld": has_json_ld,

        # Headings
        "h1_count": h1_count,
        "h2_count": h2_count,
        "heading_issues": heading_issues,

        # Images
        "total_images": total_images,
        "images_missing_alt": images_no_alt,
        "images_missing_dimensions": images_no_dimensions,
        "images_lazy_loaded": lazy_images,

        # Links
        "internal_link_count": internal_links,
        "external_link_count": external_links,
        "broken_or_js_links": broken_href,

        # Performance signals
        "render_blocking_resources": len(render_blocking),
        "preconnect_hints": preconnect_hints,
        "preload_hints": preload_hints,
        "has_web_fonts": has_web_fonts,
        "has_font_display": has_font_display,

        # Content
        "word_count": word_count,
        "cta_count": cta_count,
        "has_cookie_banner": has_cookie_banner,
        "has_popup": has_popup,
        "has_autoplay_video": autoplay_video,
        "has_hamburger_menu": has_hamburger_menu,
        "has_search": has_search,
        "has_footer": has_footer,
        "has_nav": has_nav,

        # Accessibility
        "aria_landmark_count": aria_landmarks,
        "aria_labels_count": aria_labels,
        "has_skip_link": skip_link,

        # Resources
        "inline_script_count": inline_scripts,
        "external_script_count": external_scripts,
        "inline_style_count": inline_styles,
        "external_style_count": external_styles,

        # Tech
        "detected_frameworks": frameworks,
    }


# ── Orchestrator ──────────────────────────────────────────────────────────

async def run_full_audit(url: str) -> dict:
    pagespeed_result, scrape_result, header_result = await asyncio.gather(
        run_pagespeed_audit(url),
        scrape_page(url),
        analyze_headers(url),
    )

    result = {"url": url}

    if "error" not in pagespeed_result:
        result.update(pagespeed_result)
    else:
        result.update({
            "performance_score": None,
            "accessibility_score": None,
            "seo_score": None,
            "best_practices_score": None,
            "core_web_vitals": None,
            "pagespeed_opportunities": None,
            "pagespeed_diagnostics": None,
        })

    if "error" not in scrape_result:
        result.update(scrape_result)
    else:
        result.update({
            "scrape_failed": True,
        })

    if "error" not in header_result:
        result.update(header_result)

    return result
