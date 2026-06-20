from fastapi.testclient import TestClient

from shipsense import analyzer, db
from shipsense.main import app
from shipsense.models import BehaviorEvent, CriticalFlowRequest, OnboardRequest


def event(event_id, action, user_id, timestamp):
    return {
        "event_id": event_id,
        "action": action,
        "user_id": user_id,
        "timestamp": timestamp,
    }


def test_readiness_reports_missing_step_and_close_match():
    readiness = analyzer.get_instrumentation_readiness(
        [
            event("1", "landing", "u1", "2026-06-20T12:00:00Z"),
            event("2", "signup_complete", "u1", "2026-06-20T12:01:00Z"),
        ],
        ["landing", "signup_completed"],
    )

    assert readiness["status"] == "missing_events"
    assert readiness["coverage_count"] == 1
    missing = readiness["flow_steps"][1]
    assert missing["observed"] is False
    assert missing["possible_matches"] == ["signup_complete"]
    assert readiness["decision_ready"] is False


def test_readiness_requires_transition_sample_and_detects_order_problems():
    readiness = analyzer.get_instrumentation_readiness(
        [
            event("1", "signup", "u1", "2026-06-20T12:00:00Z"),
            event("2", "landing", "u1", "2026-06-20T12:01:00Z"),
            event("3", "signup", "u2", "2026-06-20T12:02:00Z"),
            event("4", "landing", "u3", "2026-06-20T12:03:00Z"),
        ],
        ["landing", "signup"],
    )

    transition = readiness["transitions"][0]
    assert readiness["status"] == "insufficient_sample"
    assert transition["users_who_reached"] == 2
    assert transition["sample_gap"] == 3
    assert transition["orphaned_next_step_users"] == 1
    assert transition["out_of_order_users"] == 1
    assert {issue["code"] for issue in readiness["issues"]} >= {
        "insufficient_transition_sample",
        "orphaned_next_step",
        "out_of_order_transition",
    }


def test_readiness_is_ready_with_five_valid_users():
    events = []
    for index in range(5):
        events.extend([
            event(
                f"{index}-landing",
                "landing",
                f"u{index}",
                f"2026-06-20T12:0{index}:00Z",
            ),
            event(
                f"{index}-signup",
                "signup",
                f"u{index}",
                f"2026-06-20T12:1{index}:00Z",
            ),
        ])

    readiness = analyzer.get_instrumentation_readiness(
        events,
        ["landing", "signup"],
    )

    assert readiness["status"] == "ready"
    assert readiness["coverage_percent"] == 100
    assert readiness["decision_ready"] is True
    assert readiness["transitions"][0]["ready"] is True


def test_critical_flow_rejects_duplicate_steps():
    for model, payload in (
        (
            CriticalFlowRequest,
            {"steps": ["landing", "landing"]},
        ),
        (
            OnboardRequest,
            {
                "url": "https://example.com",
                "product_type": "b2b",
                "core_action": "signup",
                "critical_flow": ["landing", "landing"],
            },
        ),
    ):
        try:
            model.model_validate(payload)
        except ValueError as error:
            assert "must be unique" in str(error)
        else:
            raise AssertionError("Duplicate critical-flow steps were accepted")


def test_readiness_api_returns_product_scoped_status(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "shipsense.db"))
    with TestClient(app) as client:
        workspace = client.post("/api/workspaces").json()
        headers = {"X-Workspace-Key": workspace["workspace_key"]}
        product = client.post(
            "/api/onboard",
            headers=headers,
            json={
                "url": "https://example.com",
                "product_type": "b2b",
                "core_action": "signup",
                "critical_flow": ["landing", "signup"],
                "audit_data": {"performance_score": 95},
            },
        ).json()

        client.post(
            "/api/behavior/ingest",
            json={
                "product_id": product["product_id"],
                "collector_key": product["collector_key"],
                "events": [
                    event("1", "landing", "u1", "2026-06-20T12:00:00Z"),
                ],
            },
        )

        response = client.get(
            f"/api/product/{product['product_id']}/instrumentation-readiness",
            headers=headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["product_id"] == product["product_id"]
        assert body["collector_connected"] is True
        assert body["coverage_count"] == 1
        assert body["status"] == "missing_events"


def test_behavior_experiment_rejects_invalid_baseline(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "shipsense.db"))
    db.init_db()
    workspace = db.create_workspace()
    created = db.create_product(
        url="https://example.com",
        product_type="b2b",
        core_action="signup",
        user_id="owner",
        workspace_id=workspace["id"],
        critical_flow=["landing", "signup"],
    )
    product = db.get_product(created["id"])
    db.insert_events(product["id"], [
        BehaviorEvent(
            event_id="landing-1",
            action="landing",
            user_id="u1",
            timestamp="2026-06-20T12:00:00Z",
        ),
    ])
    decision_id, _ = db.save_decision(product["id"], {
        "title": "Reduce signup drop-off",
        "expected_outcome": "More users sign up.",
        "target_metric": "funnel:landing:signup:completion_rate",
        "baseline_value": "0%",
    })

    with TestClient(app) as client:
        response = client.post(
            "/api/experiments",
            headers={"X-Workspace-Key": workspace["workspace_key"]},
            json={
                "product_id": product["public_id"],
                "decision_id": decision_id,
            },
        )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "invalid_behavior_baseline"


def test_sample_product_is_labelled_and_closes_the_loop(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "shipsense.db"))
    with TestClient(app) as client:
        workspace = client.post("/api/workspaces").json()
        headers = {"X-Workspace-Key": workspace["workspace_key"]}

        created = client.post(
            "/api/demo/sample-product",
            headers=headers,
        )

        assert created.status_code == 200
        sample = created.json()
        assert sample["is_sample"] is True
        assert "synthetic" in sample["label"]

        product = client.get(
            f"/api/product/{sample['product_id']}",
            headers=headers,
        ).json()
        assert product["is_sample"] is True

        readiness = client.get(
            f"/api/product/{sample['product_id']}/instrumentation-readiness",
            headers=headers,
        ).json()
        assert readiness["decision_ready"] is True
        assert readiness["coverage_percent"] == 100

        experiments = client.get(
            f"/api/product/{sample['product_id']}/experiments",
            headers=headers,
        ).json()
        assert experiments[0]["status"] == "evaluated"
        assert experiments[0]["result"]["current"] == 80

        decision = client.get(
            f"/api/decision/{sample['product_id']}",
            headers=headers,
        ).json()
        assert decision["stale"] is False
