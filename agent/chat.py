from .client import _get_client
from .context import _build_context
from .prompt import SYSTEM_PROMPT


def chat_with_agent(product, message, top_actions, drop_offs, active_users, avg_session, patterns, chat_history):
    context = _build_context(product, top_actions, drop_offs, active_users, avg_session, patterns, chat_history)

    extra_instruction = (
        "You are ShipSense. Follow these rules for this response:\n"
        "1. Answer the specific question first — directly, in one sentence.\n"
        "2. Add one relevant data point from the product data.\n"
        "3. End with one follow-up insight they didn't ask for but need.\n"
        "4. Use plain English. No jargon. No padding."
    )

    messages = [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\n\nCurrent Product Data:\n{context}\n\n{extra_instruction}"},
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
