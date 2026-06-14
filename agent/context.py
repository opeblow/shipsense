def _build_context(product, top_actions, drop_offs, active_users, avg_session, patterns, chat_history):
    lines = []
    lines.append(f"Product URL: {product['url']}")
    lines.append(f"Product Type: {product['product_type']}")
    lines.append(f"Core Action: {product['core_action']}")
    lines.append(f"Active Users (7d): {active_users}")
    lines.append(f"Avg Session: {avg_session}")
    lines.append("")
    lines.append("Top Actions:")
    for a in top_actions:
        lines.append(f"  - {a['action']}: {a['count']} users ({a['frequency']})")
    lines.append("")
    lines.append("Drop-off Points:")
    for d in drop_offs:
        lines.append(f"  - {d['step']} -> {d['next_step']}: {d['drop_off_rate']} drop off")
    lines.append("")
    if patterns:
        lines.append("Detected Patterns:")
        for p in patterns:
            lines.append(f"  - {p}")
    lines.append("")
    if chat_history:
        lines.append("Previous Conversation:")
        for msg in chat_history:
            role = "User" if msg["role"] == "user" else "ShipSense"
            lines.append(f"  {role}: {msg['content']}")
    return "\n".join(lines)
