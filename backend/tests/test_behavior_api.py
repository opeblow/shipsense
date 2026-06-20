from shipsense import db, main
from shipsense.models import BehaviorEvent


def create_test_product():
    workspace = db.create_workspace()
    created = db.create_product(
        url="https://example.com",
        product_type="b2b",
        core_action="signup",
        user_id="owner",
        workspace_id=workspace["id"],
        critical_flow=["landing", "signup"],
    )
    return workspace, created, db.get_product(created["id"])


def test_behavior_response_uses_correct_metric_names(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "shipsense.db"))
    db.init_db()
    workspace, created, product = create_test_product()
    db.insert_events(product["id"], [
        BehaviorEvent(
            event_id="1",
            action="landing",
            user_id="u1",
            timestamp="2026-06-20T12:00:00Z",
        ),
        BehaviorEvent(
            event_id="2",
            action="landing",
            user_id="u1",
            timestamp="2026-06-20T12:01:00Z",
        ),
        BehaviorEvent(
            event_id="3",
            action="landing",
            user_id="u2",
            timestamp="2026-06-20T12:02:00Z",
        ),
    ])

    response = main.get_behavior(created["public_id"], workspace)
    action = response.top_actions[0]

    assert response.event_count == 3
    assert action.action == "landing"
    assert action.event_count == 3
    assert action.unique_users == 2
    assert action.event_frequency == "100%"
    assert action.user_frequency == "100%"


def test_canonical_event_field_names_are_accepted():
    event = BehaviorEvent.model_validate({
        "event_id": "evt-1",
        "schema_version": 1,
        "name": "signup_completed",
        "anonymous_id": "visitor-1",
        "session_id": "session-1",
        "occurred_at": "2026-06-20T12:00:00Z",
        "page_url": "https://example.com/signup",
        "properties": {},
    })

    assert event.action == "signup_completed"
    assert event.user_id == "visitor-1"
    assert event.timestamp == "2026-06-20T12:00:00+00:00"


def test_decision_endpoint_creates_and_versions_decisions(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "shipsense.db"))
    db.init_db()
    workspace, created, product = create_test_product()
    db.save_audit(product["id"], {"performance_score": 42})

    first = main.get_decision(created["public_id"], workspace)
    second = main.refresh_decision(created["public_id"], workspace)

    assert first.title == "Improve the product’s loading experience"
    assert first.version == 1
    assert second.version == 2
    assert second.decision_id != first.decision_id


def test_explicit_critical_flow_is_used_for_behavior(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "shipsense.db"))
    db.init_db()
    workspace, created, product = create_test_product()
    events = []
    for index in range(5):
        user = f"u{index}"
        events.append(BehaviorEvent(
            event_id=f"{user}-landing",
            action="landing",
            user_id=user,
            timestamp=f"2026-06-20T12:0{index}:00Z",
        ))
        if index < 2:
            events.append(BehaviorEvent(
                event_id=f"{user}-signup",
                action="signup",
                user_id=user,
                timestamp=f"2026-06-20T12:1{index}:00Z",
            ))
    db.insert_events(product["id"], events)

    response = main.get_behavior(created["public_id"], workspace)

    assert response.drop_off_points[0]["inferred"] is False
    assert response.drop_off_points[0]["drop_off_rate"] == "60%"
