from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from shipsense import db
from shipsense.experiments import evaluate_experiment
from shipsense.main import app


def test_technical_experiment_compares_frozen_baseline():
    status, result = evaluate_experiment(
        {
            "target_metric": "technical_audit:performance_score",
            "baseline_value": "42/100",
            "shipped_at": "2026-06-20T12:00:00+00:00",
        },
        product={},
        events=[],
        audit_data={"performance_score": 70},
    )

    assert status == "evaluated"
    assert result["conclusion"] == "improved"
    assert result["change"] == 28
    assert result["recommendation"] == "keep"


def test_behavior_experiment_requires_minimum_post_ship_sample():
    status, result = evaluate_experiment(
        {
            "target_metric": "funnel:landing:signup:completion_rate",
            "baseline_value": "40%",
            "shipped_at": "2026-06-20T12:00:00+00:00",
        },
        product={},
        events=[],
        audit_data=None,
    )

    assert status == "inconclusive"
    assert result["conclusion"] == "insufficient_data"


def test_experiment_api_closes_decision_loop(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "shipsense.db"))
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
        decision = client.get(
            f"/api/decision/{product_id}",
            headers=headers,
        ).json()

        created = client.post(
            "/api/experiments",
            headers=headers,
            json={
                "product_id": product_id,
                "decision_id": decision["decision_id"],
            },
        )
        assert created.status_code == 200
        experiment = created.json()
        assert experiment["baseline_value"] == decision["baseline_value"]
        assert experiment["status"] == "planned"

        shipped = client.post(
            f"/api/experiments/{experiment['id']}/ship",
            headers=headers,
        )
        assert shipped.status_code == 200
        assert shipped.json()["status"] == "collecting"

        product = db.get_product(product_id)
        db.save_audit(product["id"], {"performance_score": 70})
        evaluated = client.post(
            f"/api/experiments/{experiment['id']}/evaluate",
            headers=headers,
        )
        assert evaluated.status_code == 200
        assert evaluated.json()["status"] == "evaluated"
        assert evaluated.json()["result"]["conclusion"] == "improved"

        listed = client.get(
            f"/api/product/{product_id}/experiments",
            headers=headers,
        ).json()
        assert len(listed) == 1
        assert listed[0]["id"] == experiment["id"]
