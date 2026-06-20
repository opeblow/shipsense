from fastapi.testclient import TestClient

from shipsense import db
from shipsense.main import app


def test_new_event_marks_decision_stale_until_refresh(tmp_path, monkeypatch):
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

        initial = client.get(
            f"/api/decision/{product_id}",
            headers=headers,
        ).json()
        assert initial["stale"] is False

        ingest = client.post(
            "/api/behavior/ingest",
            json={
                "product_id": product_id,
                "collector_key": onboard["collector_key"],
                "events": [{
                    "event_id": "fresh-event",
                    "action": "landing",
                    "user_id": "visitor",
                    "timestamp": "2026-06-20T12:00:00Z",
                }],
            },
        )
        assert ingest.status_code == 200

        stale = client.get(
            f"/api/decision/{product_id}",
            headers=headers,
        ).json()
        assert stale["stale"] is True

        refreshed = client.post(
            f"/api/decision/{product_id}/refresh",
            headers=headers,
        ).json()
        assert refreshed["stale"] is False
        assert refreshed["version"] == initial["version"] + 1
