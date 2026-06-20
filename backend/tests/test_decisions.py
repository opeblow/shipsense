from shipsense.decisions import build_decision


PRODUCT = {
    "url": "https://example.com",
    "product_type": "b2b",
    "core_action": "create project",
}


def test_behavior_dropoff_outranks_moderate_technical_issue():
    decision = build_decision(
        PRODUCT,
        audit_data={"performance_score": 75},
        top_actions=[],
        drop_offs=[{
            "step": "signup",
            "next_step": "create project",
            "users_who_reached": 20,
            "users_who_continued": 8,
            "drop_off_rate": "60%",
            "inferred": False,
        }],
        active_users=20,
    )

    assert decision["title"] == "Reduce drop-off after signup"
    assert decision["target_metric"].endswith("completion_rate")
    assert decision["baseline_value"] == "40%"
    assert decision["evidence"][0]["sample_size"] == 20


def test_low_sample_behavior_does_not_create_false_priority():
    decision = build_decision(
        PRODUCT,
        audit_data={"performance_score": 55},
        top_actions=[],
        drop_offs=[{
            "step": "signup",
            "next_step": "create project",
            "users_who_reached": 2,
            "users_who_continued": 0,
            "drop_off_rate": "100%",
            "inferred": True,
        }],
        active_users=2,
    )

    assert decision["title"] == "Improve the product’s loading experience"
    assert decision["evidence"][0]["source_type"] == "technical_audit"


def test_missing_headline_and_cta_create_product_facing_audit_decision():
    decision = build_decision(
        PRODUCT,
        audit_data={
            "h1_count": 0,
            "cta_count": 0,
            "word_count": 9,
            "security_headers": {"security_score": 17},
        },
        top_actions=[],
        drop_offs=[],
        active_users=0,
    )

    assert decision["title"] == "Clarify the landing page’s primary action"
    assert decision["target_metric"] == "technical_audit:cta_count"
    assert [item["metric_key"] for item in decision["evidence"]] == [
        "h1_count",
        "cta_count",
        "word_count",
    ]


def test_no_evidence_returns_collection_decision():
    decision = build_decision(
        PRODUCT,
        audit_data=None,
        top_actions=[],
        drop_offs=[],
        active_users=0,
    )

    assert decision["title"] == "Collect enough evidence for a product decision"
    assert decision["evidence"] == []
    assert decision["confidence"] == 1.0
