from fastapi.testclient import TestClient

from shipsense import db
from shipsense.main import app


def test_workspace_key_is_required_and_scopes_products(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "shipsense.db"))
    with TestClient(app) as client:
        owner = client.post("/api/workspaces").json()
        stranger = client.post("/api/workspaces").json()

        onboard = client.post(
            "/api/onboard",
            headers={"X-Workspace-Key": owner["workspace_key"]},
            json={
                "url": "https://example.com",
                "product_type": "b2b",
                "core_action": "signup",
                "critical_flow": ["landing", "signup"],
                "audit_data": {"performance_score": 42},
            },
        )
        assert onboard.status_code == 200
        product_id = onboard.json()["product_id"]

        assert client.get(f"/api/product/{product_id}").status_code == 401
        assert client.get(
            f"/api/product/{product_id}",
            headers={"X-Workspace-Key": stranger["workspace_key"]},
        ).status_code == 404
        assert client.get(
            f"/api/product/{product_id}",
            headers={"X-Workspace-Key": owner["workspace_key"]},
        ).status_code == 200


def test_audit_and_onboarding_reject_private_urls(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "shipsense.db"))
    with TestClient(app) as client:
        workspace = client.post("/api/workspaces").json()
        headers = {"X-Workspace-Key": workspace["workspace_key"]}

        audit = client.post(
            "/api/audit-url",
            headers=headers,
            json={"url": "http://127.0.0.1/admin"},
        )
        assert audit.status_code == 400

        onboard = client.post(
            "/api/onboard",
            headers=headers,
            json={
                "url": "http://169.254.169.254/latest/meta-data",
                "product_type": "b2b",
                "core_action": "signup",
                "critical_flow": ["landing", "signup"],
            },
        )
        assert onboard.status_code == 400


def test_collector_key_is_required_for_ingest(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "shipsense.db"))
    with TestClient(app) as client:
        workspace = client.post("/api/workspaces").json()
        onboard = client.post(
            "/api/onboard",
            headers={"X-Workspace-Key": workspace["workspace_key"]},
            json={
                "url": "https://example.com",
                "product_type": "b2b",
                "core_action": "signup",
                "critical_flow": ["landing", "signup"],
                "audit_data": {"performance_score": 42},
            },
        ).json()

        payload = {
            "product_id": onboard["product_id"],
            "collector_key": "col_wrong",
            "events": [{
                "event_id": "evt-1",
                "action": "landing",
                "user_id": "visitor",
                "timestamp": "2026-06-20T12:00:00Z",
            }],
        }
        assert client.post("/api/behavior/ingest", json=payload).status_code == 401

        payload["collector_key"] = onboard["collector_key"]
        response = client.post("/api/behavior/ingest", json=payload)
        assert response.status_code == 200
        assert response.json()["count"] == 1

        status = client.get(
            f"/api/product/{onboard['product_id']}/collector/status",
            headers={"X-Workspace-Key": workspace["workspace_key"]},
        )
        assert status.status_code == 200
        assert status.json()["verified"] is True
        assert status.json()["event_count"] == 1

        rotated = client.post(
            f"/api/product/{onboard['product_id']}/collector/rotate",
            headers={"X-Workspace-Key": workspace["workspace_key"]},
        )
        assert rotated.status_code == 200
        new_key = rotated.json()["collector_key"]
        assert new_key != onboard["collector_key"]

        payload["events"][0]["event_id"] = "evt-2"
        assert client.post("/api/behavior/ingest", json=payload).status_code == 401
        payload["collector_key"] = new_key
        assert client.post("/api/behavior/ingest", json=payload).status_code == 200
