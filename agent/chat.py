from .client import _get_client
from .context import _build_context
from .prompt import SYSTEM_PROMPT


def chat_with_agent(product, message, top_actions, drop_offs, active_users, avg_session, patterns, chat_history, audit_data=None):
    context = _build_context(product, top_actions, drop_offs, active_users, avg_session, patterns, chat_history)

    has_real_events = active_users > 0 or len(top_actions) > 0
    has_audit = bool(audit_data) and (
        audit_data.get("performance_score") is not None or
        audit_data.get("form_field_count") is not None or
        audit_data.get("security_headers") is not None
    )

    system_content = f"{SYSTEM_PROMPT}\n\nCurrent Product Data:\n{context}"

    if has_audit:
        import json
        system_content += f"\n\nLive audit data — REAL measured fields from the actual webpage:\n{json.dumps(audit_data, indent=2)}"

    system_content += (
        "\n\n── DATA HONESTY RULES (non-negotiable) ──\n"
        "1. You ONLY have two sources of truth: (a) the live audit fields above, and (b) real Novus tracker events.\n"
        f"2. Real user events available: {'YES — use top_actions, drop_offs, active_users, avg_session above' if has_real_events else 'NO — no events have been collected yet'}.\n"
        f"3. Live audit data available: {'YES — use the measured fields in the audit JSON above' if has_audit else 'NO — audit has not run yet'}.\n"
        "4. NEVER invent drop-off percentages, user counts, session durations, or conversion rates.\n"
        "5. If asked for a metric you don't have (e.g. 'What is my conversion rate?'), say exactly: "
        "'I don't have that data yet — install the Novus tracker to collect real user events.'\n"
        "6. When audit data IS available, ground every claim in a specific measured field "
        "(e.g. 'Your performance score is 43/100' or '12 images are missing alt text').\n"
        "7. Answer the question directly first. Add one data point. End with one forward-looking insight.\n"
        "8. Plain English. No jargon. No padding. No invented numbers."
    )


    messages = [
        {"role": "system", "content": system_content},
    ]
    for msg in chat_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": message})

    try:
        llm = _get_client()
        if not llm:
            raise RuntimeError("No API key")
        resp = llm.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.5,
        )
        reply = resp.choices[0].message.content

        data_point = ""
        if drop_offs:
            data_point = f"{drop_offs[0]['step']}: {drop_offs[0]['drop_off_rate']} drop-off"
        elif top_actions:
            data_point = f"{top_actions[0]['action']}: {top_actions[0]['frequency']} of users"

        return reply, data_point

    except Exception:
        return _fallback_chat(product, message, top_actions, drop_offs, active_users, avg_session)


def _fallback_chat(product, message, top_actions, drop_offs, active_users, avg_session):
    top_action_name = top_actions[0]["action"] if top_actions else "the core feature"
    top_action_pct = top_actions[0]["frequency"] if top_actions else "a portion of"
    biggest_drop = drop_offs[0] if drop_offs else None

    lines = []
    lines.append(
        f"{top_action_pct} of your users perform '{top_action_name}'."
    )

    if biggest_drop:
        lines.append(
            f"The biggest leak is at '{biggest_drop['step']}' — "
            f"{biggest_drop['drop_off_rate']} of users drop off there."
        )
    else:
        lines.append("There isn't enough data yet to identify drop-off patterns.")

    if biggest_drop:
        session_note = (
            f" is short for a {product['product_type']} product"
            if active_users > 0
            else " will improve as more users flow through"
        )
        lines.append(
            f"One thing you didn't ask: your average session is {avg_session}."
            f"That{session_note}."
            f" If you fix the '{biggest_drop['step']}' step, both session time and "
            f"activation will go up."
        )

    reply = " ".join(lines)

    data_point = ""
    if biggest_drop:
        data_point = f"{biggest_drop['step']}: {biggest_drop['drop_off_rate']} drop-off"
    elif top_actions:
        data_point = f"{top_action_name}: {top_action_pct} of users"

    return reply, data_point
