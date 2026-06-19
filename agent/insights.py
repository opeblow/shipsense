import json

from .client import _get_client
from .context import _build_context
from .prompt import SYSTEM_PROMPT
from .prompt_audit import AUDIT_SYSTEM_PROMPT


def generate_insights(product, top_actions, drop_offs, active_users, avg_session, patterns, audit_data=None):
    """
    Generate insights using ONLY real data:
      - audit_data: live measurements from PageSpeed + HTML scrape of the user's URL
      - top_actions / drop_offs: real events ingested via the Novus tracker (if any)

    Never invents or estimates numbers.
    """

    has_real_events = active_users > 0 and len(top_actions) > 0
    has_audit = bool(audit_data) and (
        audit_data.get("performance_score") is not None or
        audit_data.get("form_field_count") is not None or
        audit_data.get("security_headers") is not None
    )

    if has_audit:
        # Primary path: real audit data exists — use measured fields only.
        prompt = f"""{AUDIT_SYSTEM_PROMPT}

Input data (real, measured — no invented values):
{json.dumps(audit_data, indent=2)}

Respond with valid JSON only, in this exact format:
{{
  "what_i_see": "...",
  "why_it_matters": "...",
  "what_to_do": "...",
  "effort": "Low/Medium/High",
  "impact": "Low/Medium/High",
  "title": "short action title"
}}"""

    elif has_real_events:
        # Secondary path: real user events from the Novus tracker.
        context = _build_context(product, top_actions, drop_offs, active_users, avg_session, patterns, [])
        prompt = f"""You are ShipSense. Analyze this REAL product data and give ONE sharp insight with ONE recommendation.

Product Data (from real user events):
{context}

Respond with valid JSON only, in this exact format:
{{
  "what_i_see": "...",
  "why_it_matters": "...",
  "what_to_do": "...",
  "effort": "Low/Medium/High",
  "impact": "Low/Medium/High",
  "title": "short action title"
}}"""

    else:
        # No real data of any kind yet — return an honest empty state.
        return _no_data_response(product)

    try:
        llm = _get_client()
        if not llm:
            raise RuntimeError("No API key")
        system = AUDIT_SYSTEM_PROMPT if has_audit else SYSTEM_PROMPT
        resp = llm.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        result = json.loads(resp.choices[0].message.content)

        summary = (
            f"WHAT I SEE:\n{result.get('what_i_see', '')}\n\n"
            f"WHY IT MATTERS:\n{result.get('why_it_matters', '')}\n\n"
            f"WHAT TO DO:\n{result.get('what_to_do', '')}\n\n"
            f"EFFORT: {result.get('effort', 'Medium')}\n"
            f"IMPACT: {result.get('impact', 'High')}"
        )
        actions = [{
            "title": result.get("title", "Address the biggest issue"),
            "description": result.get("what_to_do", ""),
            "effort": result.get("effort", "Medium"),
            "impact": result.get("impact", "High"),
            "priority": 1,
        }]

        return {"summary": summary, "recommended_actions": actions}

    except Exception:
        if has_audit:
            return _fallback_audit_insights(audit_data, product)
        if has_real_events:
            return _fallback_event_insights(product, top_actions, drop_offs, active_users, avg_session)
        return _no_data_response(product)


# ── Fallbacks (no LLM available) ─────────────────────────────────────────────

def _fallback_audit_insights(audit_data, product):
    """Generate a real insight from measured audit fields when LLM is unavailable."""
    findings = []

    perf = audit_data.get("performance_score")
    if perf is not None and perf < 50:
        findings.append({
            "what_i_see": f"Your page performance score is {perf}/100 — well below the 50-point threshold where users start abandoning.",
            "why_it_matters": "Slow pages directly kill conversions. Every 1-second delay reduces conversions by ~7%.",
            "what_to_do": "Start with the top PageSpeed opportunity shown in your audit (e.g. eliminate render-blocking resources, enable compression, lazy-load images).",
            "effort": "Medium",
            "impact": "High",
            "title": f"Fix performance score ({perf}/100)",
        })
    elif perf is not None:
        findings.append({
            "what_i_see": f"Your performance score is {perf}/100.",
            "why_it_matters": "Performance directly impacts user retention and SEO ranking.",
            "what_to_do": "Review the specific PageSpeed opportunities in your audit and address the highest ms-savings item first.",
            "effort": "Medium",
            "impact": "Medium",
            "title": f"Improve performance score ({perf}/100)",
        })

    missing_alt = audit_data.get("images_missing_alt", 0)
    if not findings and missing_alt > 0:
        findings.append({
            "what_i_see": f"{missing_alt} images are missing alt text.",
            "why_it_matters": "Missing alt text breaks accessibility for screen-reader users and hurts SEO image indexing.",
            "what_to_do": f"Add descriptive alt attributes to all {missing_alt} images. This is a quick win with zero performance cost.",
            "effort": "Low",
            "impact": "Medium",
            "title": f"Add alt text to {missing_alt} images",
        })

    rbl = audit_data.get("render_blocking_resources", 0)
    if not findings and rbl > 3:
        findings.append({
            "what_i_see": f"{rbl} render-blocking resources detected — scripts and stylesheets that delay first paint.",
            "why_it_matters": "Each blocking resource adds latency before users see anything on screen.",
            "what_to_do": "Add async/defer to non-critical scripts. Move non-critical CSS to load asynchronously.",
            "effort": "Medium",
            "impact": "High",
            "title": f"Eliminate {rbl} render-blocking resources",
        })

    if not findings:
        seo = audit_data.get("seo_score")
        if seo is not None and seo < 70:
            findings.append({
                "what_i_see": f"SEO score is {seo}/100.",
                "why_it_matters": "Low SEO scores reduce your organic traffic reach.",
                "what_to_do": "Fix the missing meta description, canonical tags, or heading structure issues flagged in your audit.",
                "effort": "Low",
                "impact": "Medium",
                "title": f"Fix SEO issues (score: {seo}/100)",
            })

    if not findings:
        findings.append({
            "what_i_see": "The URL has been audited — no critical issues detected in automated checks.",
            "why_it_matters": "A baseline audit confirms your page loads and basic technical health is OK.",
            "what_to_do": "Install the Novus tracker to start collecting real user behavior data for deeper insights.",
            "effort": "Low",
            "impact": "High",
            "title": "Install tracker to get behavioral data",
        })

    f = findings[0]
    summary = (
        f"WHAT I SEE:\n{f['what_i_see']}\n\n"
        f"WHY IT MATTERS:\n{f['why_it_matters']}\n\n"
        f"WHAT TO DO:\n{f['what_to_do']}\n\n"
        f"EFFORT: {f['effort']}\n"
        f"IMPACT: {f['impact']}"
    )
    return {
        "summary": summary,
        "recommended_actions": [{
            "title": f["title"],
            "description": f["what_to_do"],
            "effort": f["effort"],
            "impact": f["impact"],
            "priority": 1,
        }],
    }


def _fallback_event_insights(product, top_actions, drop_offs, active_users, avg_session):
    """Fallback using real tracked events when LLM is unavailable."""
    top_action_name = top_actions[0]["action"]
    top_action_pct = top_actions[0]["frequency"]
    biggest_drop = drop_offs[0] if drop_offs else None

    if biggest_drop:
        what_i_see = (
            f"{biggest_drop['drop_off_rate']} of users drop off at '{biggest_drop['step']}'. "
            f"Only {top_action_pct} complete the top action ('{top_action_name}')."
        )
        what_to_do = (
            f"Simplify or remove the '{biggest_drop['step']}' step. "
            f"If it's a form, reduce the number of fields to the bare minimum."
        )
        effort = "Low"
        title = f"Fix '{biggest_drop['step']}' drop-off"
    else:
        what_i_see = (
            f"{top_action_pct} of users perform '{top_action_name}'. "
            f"Not enough data yet to pinpoint the biggest drop-off."
        )
        what_to_do = (
            f"Drive more users through your core flow ('{product['core_action']}') "
            f"so ShipSense can detect the real friction point."
        )
        effort = "Medium"
        title = "Drive traffic to core flow"

    summary = (
        f"WHAT I SEE:\n{what_i_see}\n\n"
        f"WHY IT MATTERS:\n"
        f"Every drop-off is a user you'll never recover. Fixing this has the highest leverage.\n\n"
        f"WHAT TO DO:\n{what_to_do}\n\n"
        f"EFFORT: {effort}\n"
        f"IMPACT: High"
    )
    return {
        "summary": summary,
        "recommended_actions": [{
            "title": title,
            "description": what_to_do,
            "effort": effort,
            "impact": "High",
            "priority": 1,
        }],
    }


def _no_data_response(product):
    """Honest empty state — never invents numbers."""
    return {
        "summary": (
            f"WHAT I SEE:\n"
            f"No active users, no engagement, and no data collected for {product['url']} yet.\n\n"
            f"WHY IT MATTERS:\n"
            f"Without measured data, any insight would be a guess — and ShipSense doesn't guess.\n\n"
            f"WHAT TO DO:\n"
            f"Re-run the analysis from the onboarding page to fetch a live audit of your URL, "
            f"or install the Novus tracker snippet to start collecting real user event data.\n\n"
            f"EFFORT: Low\n"
            f"IMPACT: High"
        ),
        "recommended_actions": [{
            "title": "Run a live audit of your URL",
            "description": (
                "Go back to onboarding and let ShipSense audit your URL live. "
                "It checks PageSpeed, HTML structure, SEO, accessibility, and security headers — "
                "all from your real, live page."
            ),
            "effort": "Low",
            "impact": "High",
            "priority": 1,
        }],
    }
