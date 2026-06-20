from datetime import datetime, timedelta, timezone

from shipsense import analyzer


BASE = datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc)


def event(user, action, minutes=0, **extra):
    value = {
        "user_id": user,
        "action": action,
        "timestamp": (BASE + timedelta(minutes=minutes)).isoformat(),
    }
    value.update(extra)
    return value


def test_top_actions_separates_occurrences_from_unique_users():
    events = [
        event("u1", "view", 0),
        event("u1", "view", 1),
        event("u1", "signup", 2),
        event("u2", "view", 3),
    ]

    actions = analyzer.get_top_actions(events)

    assert actions[0] == {
        "action": "view",
        "event_count": 3,
        "unique_users": 2,
        "event_frequency": "75%",
        "user_frequency": "100%",
    }
    assert actions[1]["event_count"] == 1
    assert actions[1]["unique_users"] == 1
    assert actions[1]["event_frequency"] == "25%"
    assert actions[1]["user_frequency"] == "50%"


def test_all_users_continuing_produces_zero_drop_off():
    events = []
    for index, user in enumerate(("u1", "u2", "u3", "u4")):
        events.extend([
            event(user, "landing", index * 2),
            event(user, "signup", index * 2 + 1),
        ])

    drop_off = analyzer.calculate_drop_off(events, steps=["landing", "signup"])

    assert drop_off == [{
        "step": "landing",
        "next_step": "signup",
        "users_who_reached": 4,
        "users_who_continued": 4,
        "drop_off_rate": "0%",
        "inferred": False,
    }]


def test_funnel_counts_unique_users_and_allows_intervening_events():
    events = [
        event("u1", "landing", 0),
        event("u1", "pricing", 1),
        event("u1", "signup", 2),
        event("u1", "signup", 3),
        event("u2", "landing", 4),
        event("u3", "signup", 5),
    ]

    drop_off = analyzer.calculate_drop_off(events, steps=["landing", "signup"])

    assert drop_off[0]["users_who_reached"] == 2
    assert drop_off[0]["users_who_continued"] == 1
    assert drop_off[0]["drop_off_rate"] == "50%"


def test_funnel_requires_next_step_to_happen_after_current_step():
    events = [
        event("u1", "signup", 0),
        event("u1", "landing", 1),
        event("u2", "landing", 2),
        event("u2", "signup", 3),
    ]

    drop_off = analyzer.calculate_drop_off(events, steps=["landing", "signup"])

    assert drop_off[0]["users_who_reached"] == 2
    assert drop_off[0]["users_who_continued"] == 1


def test_inferred_transitions_are_labelled_and_count_unique_users():
    events = [
        event("u1", "landing", 0),
        event("u1", "signup", 1),
        event("u2", "landing", 2),
        event("u2", "signup", 3),
    ]

    drop_off = analyzer.calculate_drop_off(events)

    assert drop_off[0]["users_who_reached"] == 2
    assert drop_off[0]["users_who_continued"] == 2
    assert drop_off[0]["drop_off_rate"] == "0%"
    assert drop_off[0]["inferred"] is True


def test_average_session_splits_on_thirty_minute_gap():
    events = [
        event("u1", "a", 0),
        event("u1", "b", 10),
        event("u1", "c", 40),
        event("u1", "d", 45),
    ]

    summary = analyzer.get_session_summary(events)

    assert summary["session_count"] == 2
    assert summary["average_duration_seconds"] == 450
    assert summary["average_duration"] == "7m 30s"


def test_explicit_session_ids_override_inactivity_grouping():
    events = [
        event("u1", "a", 0, session_id="s1"),
        event("u1", "b", 60, session_id="s1"),
        event("u1", "c", 61, session_id="s2"),
    ]

    summary = analyzer.get_session_summary(events)

    assert summary["session_count"] == 2
    assert summary["average_duration_seconds"] == 3600


def test_duplicate_event_ids_are_ignored_by_analytics():
    events = [
        event("u1", "view", 0, event_id="same"),
        event("u1", "view", 0, event_id="same"),
    ]

    actions = analyzer.get_top_actions(events)

    assert actions[0]["event_count"] == 1


def test_malformed_events_are_excluded():
    events = [
        event("u1", "view", 0),
        {"user_id": "", "action": "view", "timestamp": "bad"},
        {"user_id": "u2", "action": "", "timestamp": BASE.isoformat()},
    ]

    actions = analyzer.get_top_actions(events)

    assert len(actions) == 1
    assert actions[0]["event_count"] == 1


def test_active_users_uses_parsed_utc_timestamps():
    now = datetime.now(timezone.utc)
    events = [
        {
            "user_id": "recent",
            "action": "view",
            "timestamp": (now - timedelta(days=1)).isoformat(),
        },
        {
            "user_id": "old",
            "action": "view",
            "timestamp": (now - timedelta(days=10)).isoformat(),
        },
    ]

    assert analyzer.get_active_users(events, days=7, now=now) == 1
