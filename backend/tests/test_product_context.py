from fastapi.testclient import TestClient

from agent.context import build_analyst_context, build_evidence_registry
from shipsense import auditor, db
from shipsense.decisions import build_decision
from shipsense.main import app


def test_scrape_extracts_interaction_context(monkeypatch):
    html = """
    <html>
      <head>
        <title>Launch faster</title>
        <meta name="description" content="Evidence for product teams">
      </head>
      <body>
        <header><nav><a href="/pricing">Pricing</a></nav></header>
        <main>
          <h1>Know what to fix next</h1>
          <a href="/signup">Start free</a>
          <button>Request demo</button>
          <form action="/signup">
            <input type="email">
            <input type="password">
            <button type="submit">Create account</button>
          </form>
        </main>
      </body>
    </html>
    """

    class Response:
        text = html

        @staticmethod
        def raise_for_status():
            return None

    monkeypatch.setattr(auditor, "safe_request", lambda *_args, **_kwargs: Response())

    result = auditor.scrape_page("https://example.com")

    assert result["h1_text"] == "Know what to fix next"
    assert result["meta_description_text"] == "Evidence for product teams"
    assert [item["text"] for item in result["primary_ctas"]] == [
        "Start free",
        "Request demo",
        "Create account",
    ]
    assert result["form_summaries"][0]["field_count"] == 2
    assert result["form_summaries"][0]["submit_text"] == "Create account"
    assert result["nav_labels"] == ["Pricing"]


def test_behavior_decision_adds_labelled_testable_hypotheses():
    decision = build_decision(
        {
            "url": "https://example.com",
            "product_type": "b2b",
            "core_action": "signup",
            "product_context": {
                "target_user": "solo founders",
            },
        },
        audit_data={
            "form_field_count": 7,
            "cta_count": 5,
            "primary_ctas": [{"text": "Learn more"}],
        },
        top_actions=[],
        drop_offs=[{
            "step": "landing",
            "next_step": "signup",
            "users_who_reached": 10,
            "users_who_continued": 4,
            "drop_off_rate": "60%",
            "inferred": False,
        }],
        active_users=10,
    )

    assert decision["title"] == "Reduce drop-off after landing"
    assert len(decision["hypotheses"]) == 3
    assert decision["hypotheses"][0]["id"] == "hypothesis:form_complexity"
    assert decision["hypotheses"][0]["confidence"] == "medium"
    assert "validation_action" in decision["hypotheses"][0]
    assert "funnel:landing:signup:drop_off_rate" in (
        decision["hypotheses"][0]["basis_evidence_ids"]
    )


def test_technical_decision_does_not_invent_behavioral_causes():
    decision = build_decision(
        {
            "url": "https://example.com",
            "product_type": "b2b",
            "core_action": "signup",
            "product_context": {},
        },
        audit_data={"performance_score": 42, "form_field_count": 8},
        top_actions=[],
        drop_offs=[],
        active_users=0,
    )

    assert decision["title"] == "Improve the product’s loading experience"
    assert decision["hypotheses"] == []


def test_product_context_round_trip_and_decision_freshness(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "shipsense.db"))
    with TestClient(app) as client:
        workspace = client.post("/api/workspaces").json()
        headers = {"X-Workspace-Key": workspace["workspace_key"]}
        created = client.post(
            "/api/onboard",
            headers=headers,
            json={
                "url": "https://example.com",
                "product_type": "b2b",
                "core_action": "signup",
                "critical_flow": ["landing", "signup"],
                "product_context": {
                    "target_user": "Small product teams",
                    "user_problem": "They do not know what to improve next",
                    "value_proposition": "One evidence-backed priority",
                    "business_goal": "Increase activation",
                    "constraints": "Low traffic",
                },
                "audit_data": {"performance_score": 75},
            },
        ).json()
        product_id = created["product_id"]

        first_decision = client.get(
            f"/api/decision/{product_id}",
            headers=headers,
        ).json()
        updated = client.put(
            f"/api/product/{product_id}/context",
            headers=headers,
            json={
                "target_user": "Solo founders",
                "user_problem": "They lack product analytics expertise",
                "value_proposition": "A decision and verification loop",
                "business_goal": "Increase activation",
                "constraints": "Fewer than 100 weekly users",
            },
        )
        assert updated.status_code == 200

        product = client.get(
            f"/api/product/{product_id}",
            headers=headers,
        ).json()
        assert product["product_context"]["target_user"] == "Solo founders"

        stale = client.get(
            f"/api/decision/{product_id}",
            headers=headers,
        ).json()
        assert first_decision["decision_id"] == stale["decision_id"]
        assert stale["stale"] is True


def test_analyst_context_separates_declared_context_from_measurements():
    product = {
        "url": "https://example.com",
        "product_type": "b2b",
        "core_action": "signup",
        "critical_flow": ["landing", "signup"],
        "product_context": {
            "target_user": "Solo founders",
            "value_proposition": "One product priority",
        },
    }
    registry = build_evidence_registry(
        product=product,
        top_actions=[],
        drop_offs=[],
        active_users=0,
        avg_session="0m 0s",
        audit_data={},
        decision=None,
        experiments=[],
    )
    context = build_analyst_context(product, None, [], registry)

    assert context["product"]["declared_context"]["target_user"] == "Solo founders"
    assert registry["product_context:target_user"]["source_type"] == "product_context"
