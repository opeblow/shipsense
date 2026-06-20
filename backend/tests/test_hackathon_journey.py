import importlib
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from shipsense import db
from shipsense.main import app


def test_complete_hackathon_product_journey(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "shipsense.db"))
    monkeypatch.setattr(
        importlib.import_module("agent.chat"),
        "_get_client",
        lambda: None,
    )

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
                "audit_data": {"performance_score": 75},
            },
        )
        assert onboard.status_code == 200
        product = onboard.json()

        baseline_start = datetime.now(timezone.utc) - timedelta(hours=2)
        baseline_events = []
        for index in range(5):
            event_time = baseline_start + timedelta(minutes=index)
            baseline_events.append({
                "event_id": f"before-{index}-landing",
                "action": "landing",
                "user_id": f"before-{index}",
                "timestamp": event_time.isoformat(),
            })
            if index < 2:
                baseline_events.append({
                    "event_id": f"before-{index}-signup",
                    "action": "signup",
                    "user_id": f"before-{index}",
                    "timestamp": (event_time + timedelta(seconds=30)).isoformat(),
                })

        assert client.post(
            "/api/behavior/ingest",
            json={
                "product_id": product["product_id"],
                "collector_key": product["collector_key"],
                "events": baseline_events,
            },
        ).status_code == 200

        stale = client.get(
            f"/api/decision/{product['product_id']}",
            headers=headers,
        ).json()
        assert stale["stale"] is True

        decision = client.post(
            f"/api/decision/{product['product_id']}/refresh",
            headers=headers,
        ).json()
        assert decision["title"] == "Reduce drop-off after landing"
        assert decision["baseline_value"] == "40%"
        assert decision["stale"] is False

        experiment = client.post(
            "/api/experiments",
            headers=headers,
            json={
                "product_id": product["product_id"],
                "decision_id": decision["decision_id"],
            },
        ).json()
        shipped = client.post(
            f"/api/experiments/{experiment['id']}/ship",
            headers=headers,
        ).json()
        shipped_at = datetime.fromisoformat(shipped["shipped_at"])

        after_events = []
        for index in range(5):
            event_time = shipped_at + timedelta(minutes=index + 1)
            after_events.append({
                "event_id": f"after-{index}-landing",
                "action": "landing",
                "user_id": f"after-{index}",
                "timestamp": event_time.isoformat(),
            })
            if index < 4:
                after_events.append({
                    "event_id": f"after-{index}-signup",
                    "action": "signup",
                    "user_id": f"after-{index}",
                    "timestamp": (event_time + timedelta(seconds=30)).isoformat(),
                })

        assert client.post(
            "/api/behavior/ingest",
            json={
                "product_id": product["product_id"],
                "collector_key": product["collector_key"],
                "events": after_events,
            },
        ).status_code == 200

        evaluated = client.post(
            f"/api/experiments/{experiment['id']}/evaluate",
            headers=headers,
        ).json()
        assert evaluated["status"] == "evaluated"
        assert evaluated["result"]["conclusion"] == "improved"
        assert evaluated["result"]["current"] == 80

        analyst = client.post(
            "/api/agent/chat",
            headers=headers,
            json={
                "product_id": product["product_id"],
                "user_id": "demo-conversation",
                "message": "Did the latest experiment work?",
            },
        ).json()
        assert analyst["citations"][0]["source_type"] == "experiment"
        assert "improved" in analyst["reply"]

        recovered = client.get("/api/products", headers=headers).json()
        assert recovered[0]["id"] == product["product_id"]
