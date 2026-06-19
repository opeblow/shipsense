import random
from datetime import datetime, timedelta
from types import SimpleNamespace
from . import db


def seed_demo_events(product_id, product):
    existing = db.get_events(product_id)
    if len(existing) > 500:
        return
    db.delete_events(product_id)

    actions_for_type = {
        "consumers": [
            "Sign up", "Browse products", "Add to cart",
            "Begin checkout", "Complete purchase", "Write review",
            "Share product", "View profile", "Search items",
            "Apply coupon", "Save for later", "Contact support",
        ],
        "b2b": [
            "Sign up", "Create workspace", "Invite team members",
            "Configure settings", "Create project", "Upload file",
            "Share document", "Set up integration", "View analytics",
            "Generate report", "Export data", "Upgrade plan",
        ],
        "internal tool": [
            "Log in", "View dashboard", "Run report",
            "Update record", "Approve request", "Export data",
            "Modify settings", "View audit log", "Create ticket",
            "Assign task", "Review changes", "Submit feedback",
        ],
    }

    user_count = random.randint(80, 150)
    days_back = random.randint(3, 14)
    actions = actions_for_type.get(product["product_type"], actions_for_type["consumers"])
    now = datetime.utcnow()

    events = []
    for uid in range(1, user_count + 1):
        user_id = f"user_{uid:04d}"
        session_start = now - timedelta(
            days=random.randint(0, days_back),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )

        steps = random.randint(2, len(actions))
        for s in range(steps):
            ts = session_start + timedelta(
                minutes=s * random.randint(1, 8),
                seconds=random.randint(0, 59),
            )
            if ts > now:
                break
            ev = SimpleNamespace(
                action=actions[s % len(actions)],
                user_id=user_id,
                timestamp=ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            events.append(ev)

            # Some users drop off randomly
            if random.random() < 0.2:
                break

    db.insert_events(product_id, events)
