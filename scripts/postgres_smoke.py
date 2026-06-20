#!/usr/bin/env python3
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from shipsense import db  # noqa: E402


def main():
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url.startswith(("postgres://", "postgresql://")):
        raise SystemExit("DATABASE_URL must point to PostgreSQL")

    db.init_db()
    if db.database_status() != "postgresql":
        raise SystemExit("Connected database is not PostgreSQL")

    workspace = db.create_workspace()
    product = db.create_product(
        url="https://example.com",
        product_type="b2b",
        core_action="signup",
        user_id="postgres-smoke",
        workspace_id=workspace["id"],
        critical_flow=["landing", "signup"],
        product_context={
            "target_user": "PostgreSQL smoke-test user",
            "business_goal": "Verify persistence",
        },
    )
    recovered = db.get_owned_product(product["public_id"], workspace["id"])
    if (
        not recovered
        or recovered["critical_flow"] != ["landing", "signup"]
        or recovered["product_context"]["business_goal"] != "Verify persistence"
    ):
        raise SystemExit("PostgreSQL product round-trip failed")

    with db.get_engine().begin() as connection:
        connection.execute(
            db.products.delete().where(db.products.c.id == product["id"])
        )
        connection.execute(
            db.workspaces.delete().where(db.workspaces.c.id == workspace["id"])
        )

    print("PostgreSQL smoke test passed")


if __name__ == "__main__":
    main()
