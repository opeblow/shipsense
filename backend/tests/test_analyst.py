import importlib

from fastapi.testclient import TestClient

from agent.context import build_analyst_context, build_evidence_registry
from shipsense import db
from shipsense.main import app


def test_evidence_registry_normalizes_decision_and_experiment_evidence():
    decision = {
        "evidence": [{
            "id": "technical_audit:performance_score",
            "source_type": "technical_audit",
            "metric_key": "performance_score",
            "value": 42,
            "unit": "score",
            "sample_size": None,
        }]
    }
    experiments = [{
        "public_id": "exp_1",
        "name": "Improve loading",
        "status": "evaluated",
        "target_metric": "technical_audit:performance_score",
        "baseline_value": "42/100",
        "result": {
            "conclusion": "improved",
            "baseline": 42,
            "current": 70,
            "change": 28,
            "recommendation": "keep",
        },
    }]

    registry = build_evidence_registry(
        product={"url": "https://example.com"},
        top_actions=[],
        drop_offs=[],
        active_users=0,
        avg_session="0m 0s",
        audit_data={"performance_score": 42},
        decision=decision,
        experiments=experiments,
    )

    assert registry["technical_audit:performance_score"]["value"] == 42
    assert registry["experiment:exp_1:result"]["value"] == "improved"


def test_invalid_model_citations_are_filtered(monkeypatch):
    chat_module = importlib.import_module("agent.chat")

    class FakeCompletions:
        @staticmethod
        def create(**_kwargs):
            message = type("Message", (), {
                "content": (
                    '{"answer":"Measured answer",'
                    '"citation_ids":["technical_audit:performance_score","invented:id"],'
                    '"follow_up":"What next?"}'
                )
            })
            choice = type("Choice", (), {"message": message})
            return type("Response", (), {"choices": [choice]})

    fake_client = type(
        "Client",
        (),
        {"chat": type("Chat", (), {"completions": FakeCompletions()})()},
    )()
    monkeypatch.setattr(chat_module, "_get_client", lambda: fake_client)

    result = chat_module.chat_with_agent(
        "What is measured?",
        {
            "evidence": [{
                "id": "technical_audit:performance_score",
                "source_type": "technical_audit",
                "label": "Performance score",
                "value": 42,
                "unit": "score",
                "sample_size": None,
            }]
        },
        [],
    )

    assert result["citation_ids"] == ["technical_audit:performance_score"]


def test_analyst_api_returns_context_and_cited_answer(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "shipsense.db"))
    chat_module = importlib.import_module("agent.chat")
    monkeypatch.setattr(chat_module, "_get_client", lambda: None)

    with TestClient(app) as client:
        workspace = client.post("/api/workspaces").json()
        headers = {"X-Workspace-Key": workspace["workspace_key"]}
        onboard = client.post(
            "/api/onboard",
            headers=headers,
            json={
                "url": "https://example.com",
                "product_type": "b2b",
                "core_action": "signup",
                "critical_flow": ["landing", "signup"],
                "audit_data": {"performance_score": 42},
            },
        ).json()
        product_id = onboard["product_id"]

        context = client.get(
            f"/api/agent/context/{product_id}",
            headers=headers,
        )
        assert context.status_code == 200
        assert context.json()["current_decision"]["title"]
        assert context.json()["suggested_questions"]
        assert context.json()["evidence_count"] > 0

        response = client.post(
            "/api/agent/chat",
            headers=headers,
            json={
                "product_id": product_id,
                "user_id": "conversation-1",
                "message": "Why is this the top priority?",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["citations"][0]["id"] == "technical_audit:performance_score"
        assert body["confidence"] == 0.82
        assert body["follow_up"]
