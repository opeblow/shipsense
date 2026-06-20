import json


AUDIT_EVIDENCE_FIELDS = {
    "performance_score": ("Performance score", "score"),
    "accessibility_score": ("Accessibility score", "score"),
    "seo_score": ("SEO score", "score"),
    "best_practices_score": ("Best-practices score", "score"),
    "images_missing_alt": ("Images missing alt text", "images"),
    "render_blocking_resources": ("Render-blocking resources", "resources"),
    "form_field_count": ("Form fields", "fields"),
    "cta_count": ("Calls to action detected", "elements"),
    "has_mobile_viewport": ("Mobile viewport present", "boolean"),
    "has_compression": ("Response compression enabled", "boolean"),
}


def _add(registry, item):
    if item["id"] not in registry:
        registry[item["id"]] = item


def build_evidence_registry(
    product,
    top_actions,
    drop_offs,
    active_users,
    avg_session,
    audit_data,
    decision,
    experiments,
):
    registry = {}

    _add(registry, {
        "id": "behavior:active_users_7d",
        "source_type": "behavior",
        "label": "Active users in the last 7 days",
        "value": active_users,
        "unit": "users",
        "sample_size": active_users,
    })
    _add(registry, {
        "id": "behavior:average_session",
        "source_type": "behavior",
        "label": "Average measurable session",
        "value": avg_session,
        "unit": "duration",
        "sample_size": None,
    })

    for action in top_actions:
        evidence_id = f"behavior:action:{action['action']}"
        _add(registry, {
            "id": evidence_id,
            "source_type": "behavior",
            "label": f"Users performing {action['action']}",
            "value": action["unique_users"],
            "unit": "users",
            "sample_size": action["unique_users"],
            "metadata": {
                "event_count": action["event_count"],
                "user_frequency": action["user_frequency"],
            },
        })

    for transition in drop_offs:
        evidence_id = (
            f"funnel:{transition['step']}:{transition['next_step']}:drop_off_rate"
        )
        _add(registry, {
            "id": evidence_id,
            "source_type": "funnel",
            "label": (
                f"Drop-off from {transition['step']} to "
                f"{transition['next_step']}"
            ),
            "value": transition["drop_off_rate"],
            "unit": "percent",
            "sample_size": transition["users_who_reached"],
            "metadata": {
                "users_who_continued": transition["users_who_continued"],
                "inferred": transition.get("inferred", True),
            },
        })

    for key, (label, unit) in AUDIT_EVIDENCE_FIELDS.items():
        value = (audit_data or {}).get(key)
        if value is not None:
            _add(registry, {
                "id": f"technical_audit:{key}",
                "source_type": "technical_audit",
                "label": label,
                "value": value,
                "unit": unit,
                "sample_size": None,
            })

    primary_ctas = (audit_data or {}).get("primary_ctas") or []
    if primary_ctas:
        _add(registry, {
            "id": "technical_audit:primary_ctas",
            "source_type": "technical_audit",
            "label": "Detected primary call-to-action labels",
            "value": [item.get("text") for item in primary_ctas if item.get("text")],
            "unit": "labels",
            "sample_size": None,
        })

    interruption_signals = {
        "popup": bool((audit_data or {}).get("has_popup")),
        "cookie_banner": bool((audit_data or {}).get("has_cookie_banner")),
        "autoplay_media": bool((audit_data or {}).get("has_autoplay_video")),
    }
    if any(interruption_signals.values()):
        _add(registry, {
            "id": "technical_audit:interaction_interruptions",
            "source_type": "technical_audit",
            "label": "Detected page interruption signals",
            "value": [
                key for key, present in interruption_signals.items() if present
            ],
            "unit": "signals",
            "sample_size": None,
        })

    for key, value in (product.get("product_context") or {}).items():
        if value:
            _add(registry, {
                "id": f"product_context:{key}",
                "source_type": "product_context",
                "label": key.replace("_", " "),
                "value": value,
                "unit": "declared_context",
                "sample_size": None,
            })

    security_score = (audit_data or {}).get("security_headers", {}).get(
        "security_score"
    )
    if security_score is not None:
        _add(registry, {
            "id": "technical_audit:security_score",
            "source_type": "technical_audit",
            "label": "Security-header score",
            "value": security_score,
            "unit": "score",
            "sample_size": None,
        })

    for item in (decision or {}).get("evidence", []):
        _add(registry, {
            "id": item["id"],
            "source_type": item["source_type"],
            "label": item["metric_key"].replace("_", " "),
            "value": item["value"],
            "unit": item["unit"],
            "sample_size": item.get("sample_size"),
            "metadata": item.get("metadata", {}),
        })

    for experiment in experiments or []:
        result = experiment.get("result")
        if not result:
            continue
        _add(registry, {
            "id": f"experiment:{experiment['public_id']}:result",
            "source_type": "experiment",
            "label": f"Experiment result: {experiment['name']}",
            "value": result.get("conclusion"),
            "unit": "result",
            "sample_size": result.get("sample_size"),
            "metadata": {
                "status": experiment["status"],
                "baseline": result.get("baseline"),
                "current": result.get("current"),
                "change": result.get("change"),
                "recommendation": result.get("recommendation"),
            },
        })

    return registry


def build_analyst_context(product, decision, experiments, evidence_registry):
    return {
        "product": {
            "url": product["url"],
            "product_type": product["product_type"],
            "core_action": product["core_action"],
            "critical_flow": product.get("critical_flow", []),
            "declared_context": product.get("product_context", {}),
        },
        "current_decision": decision,
        "experiments": [
            {
                "id": experiment["public_id"],
                "name": experiment["name"],
                "status": experiment["status"],
                "target_metric": experiment["target_metric"],
                "baseline_value": experiment["baseline_value"],
                "result": experiment.get("result"),
            }
            for experiment in experiments or []
        ],
        "evidence": list(evidence_registry.values()),
    }


def context_as_prompt(context):
    return json.dumps(context, indent=2, default=str)


def suggested_questions(decision, experiments):
    suggestions = []
    if decision:
        suggestions.extend([
            "Why is this the top priority?",
            "What evidence would change this recommendation?",
            "How should I implement this decision?",
        ])

    latest_experiment = experiments[0] if experiments else None
    if latest_experiment:
        if latest_experiment["status"] == "evaluated":
            suggestions.insert(0, "Did the latest experiment work?")
        elif latest_experiment["status"] in {"collecting", "inconclusive"}:
            suggestions.insert(0, "Do we have enough data to evaluate the experiment?")

    if not suggestions:
        suggestions = [
            "What evidence do we have right now?",
            "What data should I collect next?",
            "What can ShipSense conclude without guessing?",
        ]
    return suggestions[:4]


def _build_context(
    product,
    top_actions,
    drop_offs,
    active_users,
    avg_session,
    patterns,
    chat_history,
):
    """Legacy text context used by the insight generator during migration."""
    lines = [
        f"Product URL: {product['url']}",
        f"Product Type: {product['product_type']}",
        f"Core Action: {product['core_action']}",
        f"Declared Product Context: {json.dumps(product.get('product_context', {}))}",
        f"Active Users (7d): {active_users}",
        f"Avg Session: {avg_session}",
        "",
        "Top Actions:",
    ]
    for action in top_actions:
        lines.append(
            f"  - {action['action']}: {action['event_count']} occurrences by "
            f"{action['unique_users']} unique users "
            f"({action['user_frequency']} of measured users)"
        )
    lines.extend(["", "Drop-off Points:"])
    for transition in drop_offs:
        lines.append(
            f"  - {transition['step']} -> {transition['next_step']}: "
            f"{transition['drop_off_rate']} drop off"
        )
    if patterns:
        lines.extend(["", "Detected Patterns:"])
        lines.extend(f"  - {pattern}" for pattern in patterns)
    if chat_history:
        lines.extend(["", "Previous Conversation:"])
        for item in chat_history:
            role = "User" if item["role"] == "user" else "ShipSense"
            lines.append(f"  {role}: {item['content']}")
    return "\n".join(lines)
