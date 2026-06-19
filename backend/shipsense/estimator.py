import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agent.client import _get_client


_CACHE = {}


def _call_gpt(system, user):
    llm = _get_client()
    if not llm:
        return None
    resp = llm.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


def estimate_metrics(product):
    pid = product["id"]
    key = f"metrics:{pid}"
    if key in _CACHE:
        return _CACHE[key]

    prompt = f"""You are a web researcher. Use your training knowledge of this specific product.

Product URL: {product['url']}
Product Type: {product['product_type']}
Core Action: {product['core_action']}

Generate realistic estimated metrics for this product based on its actual public user base.

Return ONLY valid JSON:
{{
  "active_users": <realistic number based on product's actual user base>,
  "avg_session": "<Xm Xs>",
  "drop_off_rate": "<XX%>",
  "top_action": "<most common action for this product>"
}}"""

    try:
        result = _call_gpt(
            "You are a data analyst with deep knowledge of tech product metrics.",
            prompt,
        )
        if result:
            _CACHE[key] = result
        return result
    except Exception:
        return None


def estimate_behavior(product):
    pid = product["id"]
    key = f"behavior:{pid}"
    if key in _CACHE:
        return _CACHE[key]

    prompt = f"""You are a web researcher. Use your training knowledge of this specific product.

Product URL: {product['url']}
Product Type: {product['product_type']}
Core Action: {product['core_action']}

Generate realistic estimated user behavior data for this product. Use the product's actual user base size.

Return ONLY valid JSON:
{{
  "top_actions": [
    {{"action": "Sign up", "users": <realistic number>, "frequency": "<XX%>", "dropoff_after": "<XX%>"}},
    {{"action": "<next common action>", "users": <realistic number>, "frequency": "<XX%>", "dropoff_after": "<XX%>"}},
    {{"action": "<next common action>", "users": <realistic number>, "frequency": "<XX%>", "dropoff_after": "<XX%>"}},
    {{"action": "<next common action>", "users": <realistic number>, "frequency": "<XX%>", "dropoff_after": "<XX%>"}},
    {{"action": "<next common action>", "users": <realistic number>, "frequency": "<XX%>", "dropoff_after": "<XX%>"}}
  ],
  "drop_off_points": [
    {{"step": "Sign up", "next_step": "<next step>", "users_who_reached": <number>, "users_who_continued": <number>, "drop_off_rate": "<XX%>"}},
    {{"step": "<step>", "next_step": "<next step>", "users_who_reached": <number>, "users_who_continued": <number>, "drop_off_rate": "<XX%>"}},
    {{"step": "<step>", "next_step": "<next step>", "users_who_reached": <number>, "users_who_continued": <number>, "drop_off_rate": "<XX%>"}},
    {{"step": "<step>", "next_step": "<next step>", "users_who_reached": <number>, "users_who_continued": <number>, "drop_off_rate": "<XX%>"}},
    {{"step": "<step>", "next_step": "<next step>", "users_who_reached": <number>, "users_who_continued": <number>, "drop_off_rate": "<XX%>"}}
  ],
  "avg_session": "<Xm Xs>",
  "active_users": <realistic number>
}}"""

    try:
        result = _call_gpt(
            "You are a data analyst with deep knowledge of tech product user behavior.",
            prompt,
        )
        if result:
            _CACHE[key] = result
        return result
    except Exception:
        return None
