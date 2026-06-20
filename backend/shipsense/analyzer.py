from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher


SESSION_TIMEOUT = timedelta(minutes=30)
MIN_BEHAVIOR_SAMPLE = 5


def _parse_timestamp(value):
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalize_events(events):
    """Return valid, UTC-normalized, deduplicated events.

    Both the current legacy event shape and the canonical v1 shape are
    supported while the collector and storage layer are migrated.
    """
    normalized = []
    seen_event_ids = set()

    for raw in events or []:
        if not isinstance(raw, dict):
            continue

        action = raw.get("name", raw.get("action"))
        user_id = raw.get("anonymous_id", raw.get("user_id"))
        timestamp = _parse_timestamp(raw.get("occurred_at", raw.get("timestamp")))
        event_id = raw.get("event_id")

        if not isinstance(action, str) or not action.strip():
            continue
        if not isinstance(user_id, str) or not user_id.strip():
            continue
        if timestamp is None:
            continue
        if event_id:
            event_id = str(event_id)
            if event_id in seen_event_ids:
                continue
            seen_event_ids.add(event_id)

        normalized.append({
            "event_id": event_id,
            "action": action.strip()[:120],
            "user_id": user_id.strip(),
            "session_id": raw.get("session_id"),
            "timestamp": timestamp,
        })

    normalized.sort(key=lambda item: (item["timestamp"], item["user_id"], item["action"]))
    return normalized


def _percentage(numerator, denominator):
    return f"{round(numerator / denominator * 100)}%" if denominator else "0%"


def get_top_actions(events, limit=5):
    """Rank actions while separating event occurrences from unique users."""
    valid_events = _normalize_events(events)
    event_counts = Counter(event["action"] for event in valid_events)
    users_by_action = defaultdict(set)
    all_users = set()

    for event in valid_events:
        users_by_action[event["action"]].add(event["user_id"])
        all_users.add(event["user_id"])

    total_events = len(valid_events)
    total_users = len(all_users)
    ranked = sorted(
        event_counts,
        key=lambda action: (
            -event_counts[action],
            -len(users_by_action[action]),
            action,
        ),
    )

    return [
        {
            "action": action,
            "event_count": event_counts[action],
            "unique_users": len(users_by_action[action]),
            "event_frequency": _percentage(event_counts[action], total_events),
            "user_frequency": _percentage(len(users_by_action[action]), total_users),
        }
        for action in ranked[:limit]
    ]


def _events_by_user(events):
    grouped = defaultdict(list)
    for event in _normalize_events(events):
        grouped[event["user_id"]].append(event)
    return grouped


def _ordered_step_completion(user_events, current_step, next_step):
    current_times = [
        event["timestamp"]
        for event in user_events
        if event["action"] == current_step
    ]
    if not current_times:
        return False, False

    first_current = min(current_times)
    continued = any(
        event["action"] == next_step and event["timestamp"] > first_current
        for event in user_events
    )
    return True, continued


def _calculate_explicit_funnel(grouped_events, steps):
    results = []
    for current_step, next_step in zip(steps, steps[1:]):
        reached = 0
        continued = 0
        for user_events in grouped_events.values():
            did_reach, did_continue = _ordered_step_completion(
                user_events,
                current_step,
                next_step,
            )
            reached += int(did_reach)
            continued += int(did_continue)

        results.append({
            "step": current_step,
            "next_step": next_step,
            "users_who_reached": reached,
            "users_who_continued": continued,
            "drop_off_rate": _percentage(reached - continued, reached),
            "inferred": False,
        })
    return results


def _infer_transitions(grouped_events, limit):
    users_by_pair = defaultdict(set)
    users_by_action = defaultdict(set)

    for user_id, user_events in grouped_events.items():
        ordered_actions = [event["action"] for event in user_events]
        for action in set(ordered_actions):
            users_by_action[action].add(user_id)
        for current_step, next_step in zip(ordered_actions, ordered_actions[1:]):
            if current_step != next_step:
                users_by_pair[(current_step, next_step)].add(user_id)

    ranked_pairs = sorted(
        users_by_pair,
        key=lambda pair: (
            -len(users_by_pair[pair]),
            pair[0],
            pair[1],
        ),
    )

    results = []
    used_current_steps = set()
    for current_step, next_step in ranked_pairs:
        if current_step in used_current_steps:
            continue
        reached = len(users_by_action[current_step])
        continued = len(users_by_pair[(current_step, next_step)])
        results.append({
            "step": current_step,
            "next_step": next_step,
            "users_who_reached": reached,
            "users_who_continued": continued,
            "drop_off_rate": _percentage(reached - continued, reached),
            "inferred": True,
        })
        used_current_steps.add(current_step)
        if len(results) >= limit:
            break
    return results


def calculate_drop_off(events, steps=None, limit=5):
    """Calculate unique-user continuation through explicit or inferred steps."""
    grouped_events = _events_by_user(events)
    if steps is not None:
        clean_steps = [
            step.strip()
            for step in steps
            if isinstance(step, str) and step.strip()
        ]
        if len(clean_steps) < 2:
            return []
        return _calculate_explicit_funnel(grouped_events, clean_steps)
    return _infer_transitions(grouped_events, limit)


def get_active_users(events, days=7, now=None):
    """Count unique users with a valid event inside the selected UTC window."""
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    cutoff = current_time.astimezone(timezone.utc) - timedelta(days=days)
    return len({
        event["user_id"]
        for event in _normalize_events(events)
        if event["timestamp"] >= cutoff
    })


def _build_sessions(events):
    valid_events = _normalize_events(events)
    explicit_sessions = defaultdict(list)
    inferred_events_by_user = defaultdict(list)

    for event in valid_events:
        if event["session_id"]:
            explicit_sessions[(event["user_id"], str(event["session_id"]))].append(event)
        else:
            inferred_events_by_user[event["user_id"]].append(event)

    sessions = list(explicit_sessions.values())

    for user_events in inferred_events_by_user.values():
        current_session = []
        for event in user_events:
            if (
                current_session
                and event["timestamp"] - current_session[-1]["timestamp"] >= SESSION_TIMEOUT
            ):
                sessions.append(current_session)
                current_session = []
            current_session.append(event)
        if current_session:
            sessions.append(current_session)

    for session in sessions:
        session.sort(key=lambda event: event["timestamp"])
    return sessions


def _format_duration(seconds):
    rounded = max(0, round(seconds))
    minutes, remaining_seconds = divmod(rounded, 60)
    return f"{minutes}m {remaining_seconds}s"


def get_session_summary(events):
    sessions = _build_sessions(events)
    measurable_durations = []
    for session in sessions:
        if len(session) < 2:
            continue
        measurable_durations.append(
            (session[-1]["timestamp"] - session[0]["timestamp"]).total_seconds()
        )

    average_seconds = (
        round(sum(measurable_durations) / len(measurable_durations))
        if measurable_durations
        else 0
    )
    return {
        "session_count": len(sessions),
        "measurable_session_count": len(measurable_durations),
        "average_duration_seconds": average_seconds,
        "average_duration": _format_duration(average_seconds),
    }


def get_avg_session(events):
    """Backward-compatible formatted average session duration."""
    return get_session_summary(events)["average_duration"]


def detect_patterns(events):
    """Flag patterns derived only from valid, deduplicated events."""
    valid_events = _normalize_events(events)
    patterns = []
    event_counts = Counter(event["action"] for event in valid_events)
    total = len(valid_events)

    for action, count in event_counts.most_common():
        if count < max(5, total * 0.02):
            patterns.append(f"Low engagement on '{action}' — only {count} occurrences")
            break

    user_actions = defaultdict(list)
    for event in valid_events:
        user_actions[event["user_id"]].append(event["action"])

    switchers = sum(
        1
        for actions in user_actions.values()
        if len(set(actions)) >= 4 and len(actions) >= 6
    )
    if switchers > max(1, len(user_actions) * 0.2):
        patterns.append(
            f"{switchers} users switched between 4+ actions rapidly — possible confusion"
        )

    return patterns


def _similar_actions(step, observed_actions, threshold=0.65, limit=3):
    ranked = []
    normalized_step = step.casefold()
    for action in observed_actions:
        score = SequenceMatcher(
            None,
            normalized_step,
            action.casefold(),
        ).ratio()
        if score >= threshold and action != step:
            ranked.append((score, action))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [action for _, action in ranked[:limit]]


def get_instrumentation_readiness(
    events,
    steps,
    minimum_sample=MIN_BEHAVIOR_SAMPLE,
):
    """Explain whether configured behavior data can support a decision.

    Readiness is intentionally stricter than event ingestion. A connected
    collector is not enough: every configured flow step must be observed and
    every transition must have a defensible baseline sample.
    """
    valid_events = _normalize_events(events)
    clean_steps = [
        step.strip()
        for step in steps or []
        if isinstance(step, str) and step.strip()
    ]
    event_counts = Counter(event["action"] for event in valid_events)
    users_by_action = defaultdict(set)
    times_by_action = defaultdict(list)
    all_users = set()
    for event in valid_events:
        users_by_action[event["action"]].add(event["user_id"])
        times_by_action[event["action"]].append(event["timestamp"])
        all_users.add(event["user_id"])

    observed_actions = [
        {
            "action": action,
            "event_count": event_counts[action],
            "unique_users": len(users_by_action[action]),
        }
        for action in sorted(
            event_counts,
            key=lambda action: (-event_counts[action], action),
        )
    ]

    flow_steps = []
    issues = []
    next_actions = []
    for position, step in enumerate(clean_steps, start=1):
        observed = event_counts[step] > 0
        possible_matches = (
            []
            if observed
            else _similar_actions(step, event_counts.keys())
        )
        timestamps = times_by_action[step]
        flow_steps.append({
            "step": step,
            "position": position,
            "observed": observed,
            "event_count": event_counts[step],
            "unique_users": len(users_by_action[step]),
            "first_seen_at": min(timestamps).isoformat() if timestamps else None,
            "last_seen_at": max(timestamps).isoformat() if timestamps else None,
            "possible_matches": possible_matches,
        })
        if not observed:
            suggestion = (
                f"Observed a similar event: {', '.join(possible_matches)}."
                if possible_matches
                else "No similar observed event was found."
            )
            issues.append({
                "code": "missing_flow_step",
                "severity": "error",
                "step": step,
                "message": f"The configured event '{step}' has not arrived.",
                "suggestion": suggestion,
            })
            next_actions.append(
                f"Instrument '{step}' and trigger it once in the intended flow."
            )

    grouped = defaultdict(list)
    for event in valid_events:
        grouped[event["user_id"]].append(event)
    transitions = []
    for current_step, next_step in zip(clean_steps, clean_steps[1:]):
        reached = 0
        continued = 0
        orphaned = 0
        out_of_order = 0
        for user_events in grouped.values():
            current_times = [
                event["timestamp"]
                for event in user_events
                if event["action"] == current_step
            ]
            next_times = [
                event["timestamp"]
                for event in user_events
                if event["action"] == next_step
            ]
            if current_times:
                reached += 1
            if next_times and not current_times:
                orphaned += 1
                continue
            if current_times and next_times:
                first_current = min(current_times)
                if any(timestamp > first_current for timestamp in next_times):
                    continued += 1
                else:
                    out_of_order += 1

        sample_gap = max(0, minimum_sample - reached)
        ready = (
            event_counts[current_step] > 0
            and event_counts[next_step] > 0
            and reached >= minimum_sample
        )
        transitions.append({
            "step": current_step,
            "next_step": next_step,
            "users_who_reached": reached,
            "users_who_continued": continued,
            "minimum_sample": minimum_sample,
            "sample_gap": sample_gap,
            "ready": ready,
            "orphaned_next_step_users": orphaned,
            "out_of_order_users": out_of_order,
        })
        if reached < minimum_sample and event_counts[current_step] > 0:
            issues.append({
                "code": "insufficient_transition_sample",
                "severity": "warning",
                "step": current_step,
                "message": (
                    f"Only {reached} users reached '{current_step}'; "
                    f"{minimum_sample} are required."
                ),
                "suggestion": (
                    f"Collect {sample_gap} more unique "
                    f"{'user' if sample_gap == 1 else 'users'} at '{current_step}'."
                ),
            })
            next_actions.append(
                f"Collect {sample_gap} more unique "
                f"{'user' if sample_gap == 1 else 'users'} at '{current_step}'."
            )
        if orphaned:
            issues.append({
                "code": "orphaned_next_step",
                "severity": "warning",
                "step": next_step,
                "message": (
                    f"{orphaned} users emitted '{next_step}' without a measured "
                    f"'{current_step}' event."
                ),
                "suggestion": "Check that both events use the same visitor identity and flow.",
            })
        if out_of_order:
            issues.append({
                "code": "out_of_order_transition",
                "severity": "warning",
                "step": next_step,
                "message": (
                    f"{out_of_order} users emitted '{next_step}' before "
                    f"'{current_step}'."
                ),
                "suggestion": "Verify event placement and configured flow order.",
            })

    collector_connected = bool(valid_events)
    flow_configured = len(clean_steps) >= 2
    coverage_count = sum(step["observed"] for step in flow_steps)
    coverage_percent = (
        round(coverage_count / len(flow_steps) * 100)
        if flow_steps
        else 0
    )
    decision_ready = (
        collector_connected
        and flow_configured
        and coverage_count == len(flow_steps)
        and bool(transitions)
        and all(transition["ready"] for transition in transitions)
    )

    if not collector_connected:
        status = "not_connected"
        next_actions.insert(0, "Install the collector and trigger the critical flow.")
    elif not flow_configured:
        status = "flow_not_configured"
        next_actions.insert(0, "Configure at least two ordered critical-flow events.")
    elif coverage_count < len(flow_steps):
        status = "missing_events"
    elif not all(transition["ready"] for transition in transitions):
        status = "insufficient_sample"
    elif any(
        issue["code"] in {"orphaned_next_step", "out_of_order_transition"}
        for issue in issues
    ):
        status = "ready_with_warnings"
    else:
        status = "ready"

    if decision_ready and not next_actions:
        next_actions.append("Refresh the Decision Card using the verified baseline.")

    # Preserve order while avoiding duplicate actions caused by shared steps.
    next_actions = list(dict.fromkeys(next_actions))

    return {
        "collector_connected": collector_connected,
        "event_count": len(valid_events),
        "last_event_at": (
            max(event["timestamp"] for event in valid_events).isoformat()
            if valid_events
            else None
        ),
        "flow_configured": flow_configured,
        "configured_steps": clean_steps,
        "coverage_count": coverage_count,
        "coverage_percent": coverage_percent,
        "unique_users": len(all_users),
        "minimum_sample": minimum_sample,
        "decision_ready": decision_ready,
        "status": status,
        "flow_steps": flow_steps,
        "transitions": transitions,
        "observed_actions": observed_actions,
        "issues": issues,
        "next_actions": next_actions,
    }
