from collections import Counter, defaultdict
from datetime import datetime, timedelta


def get_top_actions(events, limit=5):
    """Rank user actions by frequency."""
    counter = Counter(e["action"] for e in events)
    total = len(events)
    result = []
    for action, count in counter.most_common(limit):
        result.append({
            "action": action,
            "count": count,
            "frequency": f"{round(count / total * 100)}%" if total else "0%",
        })
    return result


def calculate_drop_off(events):
    """Calculate drop-off between sequential actions per user."""
    user_sequences = defaultdict(list)
    for e in events:
        user_sequences[e["user_id"]].append((e["timestamp"], e["action"]))

    for uid in user_sequences:
        user_sequences[uid].sort(key=lambda x: x[0])

    action_pairs = Counter()
    pair_users = Counter()

    for uid, seq in user_sequences.items():
        actions = [s[1] for s in seq]
        for i in range(len(actions) - 1):
            pair = (actions[i], actions[i + 1])
            action_pairs[pair] += 1
            pair_users[pair] = 1

    total_users = len(user_sequences)
    drop_offs = []
    seen_actions = set()

    for (from_action, to_action), count in action_pairs.most_common():
        if from_action not in seen_actions:
            from_total = sum(
                1 for seq in user_sequences.values()
                if any(s[1] == from_action for s in seq)
            )
            went_further = pair_users[(from_action, to_action)]
            drop_rate = round((1 - went_further / from_total) * 100) if from_total > 0 else 0
            drop_offs.append({
                "step": from_action,
                "next_step": to_action,
                "users_who_reached": from_total,
                "users_who_continued": went_further,
                "drop_off_rate": f"{drop_rate}%",
            })
            seen_actions.add(from_action)

    return drop_offs[:5]


def get_active_users(events, days=7):
    """Count unique users in the last N days."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    unique = set(
        e["user_id"] for e in events if e["timestamp"] >= cutoff
    )
    return len(unique)


def get_avg_session(events):
    """Estimate average session duration from event timestamps."""
    user_timestamps = defaultdict(list)
    for e in events:
        try:
            ts = datetime.fromisoformat(e["timestamp"])
        except (ValueError, TypeError):
            continue
        user_timestamps[e["user_id"]].append(ts)

    durations = []
    for uid, timestamps in user_timestamps.items():
        timestamps.sort()
        if len(timestamps) < 2:
            continue
        # Consider events within 30 min as same session
        session_start = timestamps[0]
        session_end = timestamps[0]
        for ts in timestamps[1:]:
            if (ts - session_end).total_seconds() < 1800:
                session_end = ts
            else:
                durations.append((session_end - session_start).total_seconds())
                session_start = ts
                session_end = ts
        if session_end != session_start:
            durations.append((session_end - session_start).total_seconds())

    if not durations:
        return "0m 0s"

    avg_seconds = sum(durations) / len(durations)
    minutes = int(avg_seconds // 60)
    seconds = int(avg_seconds % 60)
    return f"{minutes}m {seconds}s"


def detect_patterns(events):
    """Flag unusual patterns worth noting."""
    patterns = []
    actions = [e["action"] for e in events]
    counter = Counter(actions)
    total = len(events)

    # Find actions with very low completion
    for action, count in counter.most_common():
        if count < max(5, total * 0.02):
            patterns.append(f"Low engagement on '{action}' — only {count} occurrences")
            break

    # Check for rapid action switching (confusion signal)
    user_actions = defaultdict(list)
    for e in events:
        user_actions[e["user_id"]].append(e["action"])

    switchers = 0
    for uid, acts in user_actions.items():
        unique_actions = set(acts)
        if len(unique_actions) >= 4 and len(acts) >= 6:
            switchers += 1

    if switchers > max(1, len(user_actions) * 0.2):
        patterns.append(f"{switchers} users switched between 4+ actions rapidly — possible confusion")

    return patterns
