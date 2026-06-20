from shipsense import db
from shipsense.models import BehaviorEvent


def create_test_product():
    workspace = db.create_workspace()
    created = db.create_product(
        url="https://example.com",
        product_type="b2b",
        core_action="create project",
        user_id="owner",
        workspace_id=workspace["id"],
        critical_flow=["landing", "create project"],
    )
    return workspace, created


def test_event_ids_are_persisted_and_deduplicated(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "shipsense.db"))
    db.init_db()
    _, created = create_test_product()
    event = BehaviorEvent(
        event_id="evt-1",
        action="create project",
        user_id="visitor-1",
        session_id="session-1",
        timestamp="2026-06-20T12:00:00Z",
        page_url="https://example.com/projects",
        properties={"source": "button"},
    )

    assert db.insert_events(created["id"], [event, event]) == 1

    stored = db.get_events(created["id"])
    assert len(stored) == 1
    assert stored[0]["event_id"] == "evt-1"
    assert stored[0]["session_id"] == "session-1"
    assert stored[0]["page_url"] == "https://example.com/projects"


def test_decisions_are_versioned(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "shipsense.db"))
    db.init_db()
    _, created = create_test_product()

    first_id, first_version = db.save_decision(created["id"], {"title": "First"})
    second_id, second_version = db.save_decision(created["id"], {"title": "Second"})

    assert first_id != second_id
    assert first_version == 1
    assert second_version == 2
    assert db.get_latest_decision(created["id"])["title"] == "Second"
    assert db.get_latest_decision(created["id"])["version"] == 2


def test_workspace_ownership_and_collector_keys_are_scoped(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "shipsense.db"))
    db.init_db()
    owner, created = create_test_product()
    stranger = db.create_workspace()

    assert db.get_owned_product(created["public_id"], owner["id"]) is not None
    assert db.get_owned_product(created["public_id"], stranger["id"]) is None
    assert db.verify_collector_key(created["public_id"], created["collector_key"]) is not None
    assert db.verify_collector_key(created["public_id"], "col_wrong") is None
