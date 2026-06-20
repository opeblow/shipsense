from datetime import datetime, timezone


MIN_BEHAVIOR_SAMPLE = 5


def _evidence(
    evidence_id,
    source_type,
    metric_key,
    value,
    unit,
    sample_size=None,
    metadata=None,
):
    return {
        "id": evidence_id,
        "source_type": source_type,
        "metric_key": metric_key,
        "value": value,
        "unit": unit,
        "sample_size": sample_size,
        "metadata": metadata or {},
    }


def _candidate(
    score,
    title,
    problem,
    evidence,
    recommendation,
    expected_outcome,
    target_metric,
    baseline_value,
    effort,
    impact,
    confidence,
    confidence_reasons,
    invalidating_conditions,
    affected_flow=None,
):
    return {
        "_score": score,
        "title": title,
        "problem": problem,
        "evidence": evidence,
        "affected_flow": affected_flow,
        "recommendation": recommendation,
        "expected_outcome": expected_outcome,
        "target_metric": target_metric,
        "baseline_value": baseline_value,
        "effort": effort,
        "impact": impact,
        "confidence": confidence,
        "confidence_reasons": confidence_reasons,
        "invalidating_conditions": invalidating_conditions,
    }


def _percent_number(value):
    if isinstance(value, str) and value.endswith("%"):
        try:
            return int(value[:-1])
        except ValueError:
            return None
    return None


def _behavior_candidates(drop_offs):
    candidates = []
    for transition in drop_offs or []:
        reached = transition.get("users_who_reached", 0)
        continued = transition.get("users_who_continued", 0)
        drop_rate = _percent_number(transition.get("drop_off_rate"))
        if reached < MIN_BEHAVIOR_SAMPLE or drop_rate is None or drop_rate < 20:
            continue

        inferred = transition.get("inferred", True)
        evidence = [
            _evidence(
                (
                    f"funnel:{transition['step']}:{transition['next_step']}:"
                    "drop_off_rate"
                ),
                "funnel",
                "drop_off_rate",
                drop_rate,
                "percent",
                sample_size=reached,
                metadata={
                    "step": transition["step"],
                    "next_step": transition["next_step"],
                    "users_who_continued": continued,
                    "inferred": inferred,
                },
            )
        ]
        confidence = 0.78 if reached >= 20 and not inferred else 0.62 if reached >= 10 else 0.48
        reasons = [
            f"Based on {reached} unique users who reached this step.",
            (
                "The flow order was explicitly configured."
                if not inferred
                else "The transition was inferred from event order and should be confirmed."
            ),
        ]
        candidates.append(_candidate(
            score=120 + drop_rate + min(reached, 50),
            title=f"Reduce drop-off after {transition['step']}",
            problem=(
                f"{drop_rate}% of measured users who reached "
                f"'{transition['step']}' did not continue to "
                f"'{transition['next_step']}'."
            ),
            evidence=evidence,
            affected_flow=f"{transition['step']} → {transition['next_step']}",
            recommendation=(
                f"Review the '{transition['step']}' step for unnecessary work, "
                f"unclear copy, or a weak next action. Make one focused change "
                f"that makes '{transition['next_step']}' the obvious continuation."
            ),
            expected_outcome=(
                f"More users continue from '{transition['step']}' to "
                f"'{transition['next_step']}'."
            ),
            target_metric=(
                f"funnel:{transition['step']}:{transition['next_step']}:"
                "completion_rate"
            ),
            baseline_value=f"{100 - drop_rate}%",
            effort="Medium",
            impact="High",
            confidence=confidence,
            confidence_reasons=reasons,
            invalidating_conditions=[
                "The inferred transition is not part of the intended product flow.",
                "Traffic sources or user mix change materially during verification.",
                "The sample remains below the minimum needed for a stable conclusion.",
            ],
        ))
    return candidates


def _audit_candidates(audit):
    if not audit:
        return []
    candidates = []

    h1_count = audit.get("h1_count")
    cta_count = audit.get("cta_count")
    word_count = audit.get("word_count")
    missing_h1 = isinstance(h1_count, int) and h1_count == 0
    missing_cta = isinstance(cta_count, int) and cta_count == 0
    sparse_copy = isinstance(word_count, int) and word_count < 80
    if missing_h1 or missing_cta:
        evidence = []
        if isinstance(h1_count, int):
            evidence.append(_evidence(
                "technical_audit:h1_count",
                "technical_audit",
                "h1_count",
                h1_count,
                "count",
            ))
        if isinstance(cta_count, int):
            evidence.append(_evidence(
                "technical_audit:cta_count",
                "technical_audit",
                "cta_count",
                cta_count,
                "count",
            ))
        if isinstance(word_count, int):
            evidence.append(_evidence(
                "technical_audit:word_count",
                "technical_audit",
                "word_count",
                word_count,
                "words",
            ))
        issue_parts = []
        if missing_h1:
            issue_parts.append("no primary H1 headline")
        if missing_cta:
            issue_parts.append("no detected call to action")
        if sparse_copy:
            issue_parts.append(f"only {word_count} words of visible page copy")
        candidates.append(_candidate(
            score=155 if missing_h1 and missing_cta else 118,
            title="Clarify the landing page’s primary action",
            problem=(
                "The live page has " + ", ".join(issue_parts) + "."
            ),
            evidence=evidence,
            affected_flow="First visit to core action",
            recommendation=(
                "Add a clear headline that states the product outcome, then add "
                "one visually dominant call to action that leads to the core "
                "product action."
            ),
            expected_outcome=(
                "New visitors can understand what the product does and what to do next."
            ),
            target_metric=(
                "technical_audit:cta_count"
                if missing_cta
                else "technical_audit:h1_count"
            ),
            baseline_value=(
                f"{cta_count} detected CTAs"
                if isinstance(cta_count, int)
                else f"{h1_count} H1 headings"
            ),
            effort="Low",
            impact="High",
            confidence=0.83,
            confidence_reasons=[
                "The page structure was inspected directly from the live HTML.",
                "Headline and CTA presence are verifiable without estimating user behavior.",
            ],
            invalidating_conditions=[
                "The submitted URL is not the page where new users decide what to do.",
                "The primary action is intentionally handled outside the audited HTML.",
            ],
        ))

    performance = audit.get("performance_score")
    if performance is not None and performance < 90:
        severity = 90 - performance
        candidates.append(_candidate(
            score=70 + severity,
            title="Improve the product’s loading experience",
            problem=f"The measured performance score is {performance}/100.",
            evidence=[_evidence(
                "technical_audit:performance_score",
                "technical_audit",
                "performance_score",
                performance,
                "score",
            )],
            affected_flow="First visit and page load",
            recommendation=(
                "Implement the highest-savings PageSpeed opportunity first, then "
                "rerun the same audit before making another performance change."
            ),
            expected_outcome="Users reach usable content faster.",
            target_metric="technical_audit:performance_score",
            baseline_value=f"{performance}/100",
            effort="Medium",
            impact="High" if performance < 50 else "Medium",
            confidence=0.82,
            confidence_reasons=[
                "The score comes from a live PageSpeed measurement.",
                "The recommendation can be verified by rerunning the same audit.",
            ],
            invalidating_conditions=[
                "The audit was affected by a temporary hosting or network incident.",
                "The tested page is not part of the product’s important user flow.",
            ],
        ))

    if audit.get("has_mobile_viewport") is False:
        candidates.append(_candidate(
            score=115,
            title="Restore a usable mobile viewport",
            problem="The page does not expose a mobile viewport declaration.",
            evidence=[_evidence(
                "technical_audit:has_mobile_viewport",
                "technical_audit",
                "has_mobile_viewport",
                False,
                "boolean",
            )],
            affected_flow="All mobile product flows",
            recommendation=(
                "Add a responsive viewport declaration and verify the critical "
                "flow at common mobile widths."
            ),
            expected_outcome="Mobile visitors can use the intended responsive layout.",
            target_metric="technical_audit:has_mobile_viewport",
            baseline_value="missing",
            effort="Low",
            impact="High",
            confidence=0.92,
            confidence_reasons=["The viewport declaration was checked directly in the live HTML."],
            invalidating_conditions=[
                "The submitted URL is not intended to support mobile devices.",
            ],
        ))

    missing_alt = audit.get("images_missing_alt")
    if isinstance(missing_alt, int) and missing_alt > 0:
        candidates.append(_candidate(
            score=45 + min(missing_alt, 20),
            title="Make product images understandable without sight",
            problem=f"{missing_alt} measured images are missing alt text.",
            evidence=[_evidence(
                "technical_audit:images_missing_alt",
                "technical_audit",
                "images_missing_alt",
                missing_alt,
                "images",
            )],
            affected_flow="Pages containing informative images",
            recommendation=(
                "Add concise alt text to informative images and empty alt "
                "attributes to decorative images."
            ),
            expected_outcome="Screen-reader users receive equivalent image context.",
            target_metric="technical_audit:images_missing_alt",
            baseline_value=str(missing_alt),
            effort="Low",
            impact="Medium",
            confidence=0.9,
            confidence_reasons=["Image alt attributes were inspected directly in the live HTML."],
            invalidating_conditions=[
                "The detected images are all decorative and already handled outside the HTML response.",
            ],
        ))

    security = audit.get("security_headers") or {}
    security_score = security.get("security_score")
    if security_score is not None and security_score < 50:
        candidates.append(_candidate(
            score=80 + (50 - security_score),
            title="Add baseline browser security protections",
            problem=f"The measured security-header score is {security_score}/100.",
            evidence=[_evidence(
                "technical_audit:security_score",
                "technical_audit",
                "security_score",
                security_score,
                "score",
            )],
            affected_flow="Every browser request",
            recommendation=(
                "Add the missing high-value response headers, beginning with "
                "Content-Security-Policy, HSTS, and frame protections where applicable."
            ),
            expected_outcome="The browser receives stronger default protections.",
            target_metric="technical_audit:security_score",
            baseline_value=f"{security_score}/100",
            effort="Medium",
            impact="High",
            confidence=0.86,
            confidence_reasons=["The headers were measured from the live HTTP response."],
            invalidating_conditions=[
                "A CDN or reverse proxy intentionally strips headers only for the audit request.",
            ],
        ))

    return candidates


def _behavior_hypotheses(selected, audit_data, product):
    """Return testable causes without promoting them to measured findings."""
    metric = selected.get("target_metric", "")
    if not metric.startswith("funnel:"):
        return []

    _, step, next_step, _ = metric.split(":", 3)
    funnel_id = f"funnel:{step}:{next_step}:drop_off_rate"
    audit = audit_data or {}
    hypotheses = []

    form_fields = audit.get("form_field_count")
    if isinstance(form_fields, int) and form_fields >= 5:
        hypotheses.append({
            "id": "hypothesis:form_complexity",
            "statement": (
                f"The '{step}' step may ask for too much information before "
                f"users can continue to '{next_step}'."
            ),
            "basis_evidence_ids": [
                funnel_id,
                "technical_audit:form_field_count",
            ],
            "confidence": "medium",
            "rationale": (
                f"The public page exposes {form_fields} form fields, but "
                "ShipSense has not observed users interacting with individual fields."
            ),
            "validation_action": (
                "Review the fields required at this step and test removing or "
                "deferring one nonessential field."
            ),
        })

    cta_count = audit.get("cta_count")
    if isinstance(cta_count, int) and cta_count >= 4:
        hypotheses.append({
            "id": "hypothesis:competing_actions",
            "statement": (
                f"Competing calls to action may make '{next_step}' less obvious."
            ),
            "basis_evidence_ids": [
                funnel_id,
                "technical_audit:cta_count",
            ],
            "confidence": "low",
            "rationale": (
                f"The public page contains {cta_count} detected calls to action. "
                "This is structural context, not proof that users were distracted."
            ),
            "validation_action": (
                f"Make the control leading to '{next_step}' visually dominant "
                "and compare the same completion metric."
            ),
        })

    interruption_signals = [
        label
        for key, label in (
            ("has_popup", "popup"),
            ("has_cookie_banner", "cookie banner"),
            ("has_autoplay_video", "autoplay media"),
        )
        if audit.get(key)
    ]
    if interruption_signals:
        hypotheses.append({
            "id": "hypothesis:page_interruption",
            "statement": (
                f"Page interruptions may compete with the transition to '{next_step}'."
            ),
            "basis_evidence_ids": [
                funnel_id,
                "technical_audit:interaction_interruptions",
            ],
            "confidence": "low",
            "rationale": (
                "The public page contains " + ", ".join(interruption_signals) +
                ". ShipSense has not measured whether users interacted with them."
            ),
            "validation_action": (
                "Temporarily suppress nonessential interruptions during the "
                "critical flow and compare continuation."
            ),
        })

    primary_ctas = [
        item.get("text", "")
        for item in audit.get("primary_ctas") or []
        if item.get("text")
    ]
    next_tokens = {
        token.casefold()
        for token in next_step.replace("_", " ").replace("-", " ").split()
        if len(token) >= 4
    }
    cta_tokens = {
        token.casefold().strip(".,:;!?")
        for text in primary_ctas
        for token in text.split()
    }
    if primary_ctas and next_tokens and not next_tokens.intersection(cta_tokens):
        hypotheses.append({
            "id": "hypothesis:continuation_language",
            "statement": (
                f"The visible CTA language may not clearly signal '{next_step}'."
            ),
            "basis_evidence_ids": [
                funnel_id,
                "technical_audit:primary_ctas",
            ],
            "confidence": "low",
            "rationale": (
                "The detected CTA labels do not share meaningful words with the "
                "configured next-step event. Event names and customer-facing copy "
                "may still intentionally differ."
            ),
            "validation_action": (
                f"Check whether users can predict that the primary CTA leads to "
                f"'{next_step}', then test more explicit copy."
            ),
        })

    if not hypotheses:
        context = product.get("product_context") or {}
        target_user = context.get("target_user") or "the intended user"
        hypotheses.append({
            "id": "hypothesis:unclear_transition",
            "statement": (
                f"The transition from '{step}' to '{next_step}' may be unclear "
                f"or require more effort than {target_user} expects."
            ),
            "basis_evidence_ids": [funnel_id],
            "confidence": "low",
            "rationale": (
                "The drop-off location is measured, but ShipSense has no direct "
                "interaction evidence identifying the cause."
            ),
            "validation_action": (
                "Observe five users attempting this transition or instrument the "
                "main controls within the step before choosing a UI change."
            ),
        })

    return hypotheses[:3]


def build_decision(
    product,
    audit_data,
    top_actions,
    drop_offs,
    active_users,
    instrumentation_readiness=None,
):
    candidates = [
        *_behavior_candidates(drop_offs),
        *_audit_candidates(audit_data),
    ]

    if candidates:
        selected = max(candidates, key=lambda item: item["_score"])
        selected = {key: value for key, value in selected.items() if key != "_score"}
    else:
        readiness = instrumentation_readiness or {}
        coverage_count = readiness.get("coverage_count", 0)
        configured_steps = readiness.get("configured_steps") or []
        next_actions = readiness.get("next_actions") or []
        primary_action = (
            next_actions[0]
            if next_actions
            else (
                "Install the ShipSense Event Collector, define the critical flow, "
                "and collect at least five users before evaluating drop-off."
            )
        )
        readiness_evidence = []
        if configured_steps:
            readiness_evidence.append(_evidence(
                "instrumentation:flow_coverage",
                "instrumentation",
                "flow_coverage",
                coverage_count,
                "steps",
                metadata={
                    "configured_steps": len(configured_steps),
                    "status": readiness.get("status", "unknown"),
                },
            ))
        selected = _candidate(
            score=0,
            title="Collect enough evidence for a product decision",
            problem="ShipSense does not yet have enough measured evidence to recommend a product change.",
            evidence=readiness_evidence,
            affected_flow=product.get("core_action"),
            recommendation=primary_action,
            expected_outcome="ShipSense can identify a defensible product priority.",
            target_metric="behavior:active_users",
            baseline_value=str(active_users),
            effort="Low",
            impact="High",
            confidence=1.0,
            confidence_reasons=["The absence of sufficient behavioral evidence is known."],
            invalidating_conditions=[
                "A new technical audit or behavior snapshot reveals a higher-priority issue.",
            ],
        )
        selected.pop("_score")

    return {
        **selected,
        "hypotheses": _behavior_hypotheses(selected, audit_data, product),
        "status": "proposed",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_snapshot_id": "latest",
    }
