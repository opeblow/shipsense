import hashlib
import json
import os
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    func,
    inspect,
    select,
)


DB_PATH = os.getenv("DATABASE_URL", "./shipsense.db")
metadata = MetaData()
_engines = {}


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


workspaces = Table(
    "workspaces",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("public_id", String(80), nullable=False, unique=True),
    Column("key_hash", String(64), nullable=False, unique=True),
    Column("created_at", String, nullable=False, default=_utc_now),
)

products = Table(
    "products",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("public_id", String(80), unique=True),
    Column("workspace_id", Integer, ForeignKey("workspaces.id")),
    Column("collector_key_hash", String(64)),
    Column("critical_flow", Text, nullable=False, server_default="[]"),
    Column("product_context", Text, nullable=False, server_default="{}"),
    Column("evidence_updated_at", String, nullable=False, default=_utc_now),
    Column("url", Text, nullable=False),
    Column("product_type", String(40), nullable=False),
    Column("core_action", Text, nullable=False),
    Column("user_id", Text, nullable=False),
    Column("created_at", String, nullable=False, default=_utc_now),
)

events = Table(
    "events",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("product_id", Integer, ForeignKey("products.id"), nullable=False),
    Column("event_id", String(160)),
    Column("schema_version", Integer, nullable=False, server_default="1"),
    Column("action", String(120), nullable=False),
    Column("user_id", Text, nullable=False),
    Column("session_id", Text),
    Column("timestamp", String, nullable=False),
    Column("page_url", Text),
    Column("properties", Text, nullable=False, server_default="{}"),
    Column("created_at", String, nullable=False, default=_utc_now),
    UniqueConstraint("product_id", "event_id", name="uq_events_product_event_id"),
)

insights = Table(
    "insights",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("product_id", Integer, ForeignKey("products.id"), nullable=False),
    Column("summary", Text, nullable=False),
    Column("actions", Text, nullable=False),
    Column("created_at", String, nullable=False, default=_utc_now),
)

chat_history = Table(
    "chat_history",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("product_id", Integer, ForeignKey("products.id"), nullable=False),
    Column("user_id", Text, nullable=False),
    Column("role", String(20), nullable=False),
    Column("content", Text, nullable=False),
    Column("created_at", String, nullable=False, default=_utc_now),
)

audits = Table(
    "audits",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("product_id", Integer, ForeignKey("products.id"), nullable=False),
    Column("audit_json", Text, nullable=False),
    Column("created_at", String, nullable=False, default=_utc_now),
)

decisions = Table(
    "decisions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("product_id", Integer, ForeignKey("products.id"), nullable=False),
    Column("version", Integer, nullable=False),
    Column("decision_json", Text, nullable=False),
    Column("created_at", String, nullable=False, default=_utc_now),
    UniqueConstraint("product_id", "version", name="uq_decisions_product_version"),
)

experiments = Table(
    "experiments",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("public_id", String(80), nullable=False, unique=True),
    Column("product_id", Integer, ForeignKey("products.id"), nullable=False),
    Column("decision_id", Integer, ForeignKey("decisions.id"), nullable=False),
    Column("name", Text, nullable=False),
    Column("hypothesis", Text, nullable=False),
    Column("target_metric", Text, nullable=False),
    Column("baseline_value", Text, nullable=False),
    Column("status", String(24), nullable=False, server_default="planned"),
    Column("shipped_at", String),
    Column("result_json", Text),
    Column("created_at", String, nullable=False, default=_utc_now),
)

Index("idx_products_workspace", products.c.workspace_id)
Index("idx_events_product", events.c.product_id)
Index("idx_events_timestamp", events.c.timestamp)
Index("idx_chat_product", chat_history.c.product_id)
Index("idx_decisions_product", decisions.c.product_id)
Index("idx_experiments_product", experiments.c.product_id)


def _database_url():
    if "://" in DB_PATH:
        if DB_PATH.startswith("postgres://"):
            return DB_PATH.replace("postgres://", "postgresql+psycopg://", 1)
        if DB_PATH.startswith("postgresql://"):
            return DB_PATH.replace("postgresql://", "postgresql+psycopg://", 1)
        return DB_PATH
    return f"sqlite:///{Path(DB_PATH).resolve()}"


def get_engine():
    url = _database_url()
    if url not in _engines:
        kwargs = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
        _engines[url] = create_engine(url, **kwargs)
    return _engines[url]


def database_status():
    engine = get_engine()
    with engine.connect() as connection:
        connection.execute(select(1)).scalar_one()
    return engine.dialect.name


def init_db():
    engine = get_engine()
    metadata.create_all(engine)
    if engine.dialect.name == "sqlite":
        _migrate_legacy_sqlite(engine)
    _migrate_product_context(engine)
    _backfill_product_identity(engine)


def _migrate_product_context(engine):
    inspector = inspect(engine)
    if "products" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("products")}
    if "product_context" not in existing:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE products ADD COLUMN "
                "product_context TEXT NOT NULL DEFAULT '{}'"
            )


def _migrate_legacy_sqlite(engine):
    inspector = inspect(engine)
    if "products" in inspector.get_table_names():
        existing = {column["name"] for column in inspector.get_columns("products")}
        additions = {
            "public_id": "TEXT",
            "workspace_id": "INTEGER",
            "collector_key_hash": "TEXT",
            "critical_flow": "TEXT NOT NULL DEFAULT '[]'",
            "product_context": "TEXT NOT NULL DEFAULT '{}'",
            "evidence_updated_at": "TEXT",
        }
        with engine.begin() as connection:
            for name, definition in additions.items():
                if name not in existing:
                    connection.exec_driver_sql(
                        f"ALTER TABLE products ADD COLUMN {name} {definition}"
                    )

    inspector = inspect(engine)
    if "events" in inspector.get_table_names():
        existing = {column["name"] for column in inspector.get_columns("events")}
        additions = {
            "event_id": "TEXT",
            "schema_version": "INTEGER NOT NULL DEFAULT 1",
            "session_id": "TEXT",
            "page_url": "TEXT",
            "properties": "TEXT NOT NULL DEFAULT '{}'",
        }
        with engine.begin() as connection:
            for name, definition in additions.items():
                if name not in existing:
                    connection.exec_driver_sql(
                        f"ALTER TABLE events ADD COLUMN {name} {definition}"
                    )
            connection.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_events_product_event_id "
                "ON events(product_id, event_id) WHERE event_id IS NOT NULL"
            )
            connection.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_products_public_id "
                "ON products(public_id) WHERE public_id IS NOT NULL"
            )


def _hash_key(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _new_public_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex}"


def _new_secret(prefix):
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def _backfill_product_identity(engine):
    with engine.begin() as connection:
        legacy = connection.execute(
            select(workspaces.c.id).where(workspaces.c.public_id == "ws_legacy")
        ).first()
        if legacy:
            legacy_workspace_id = legacy.id
        else:
            result = connection.execute(
                workspaces.insert().values(
                    public_id="ws_legacy",
                    key_hash=_hash_key(_new_secret("wsk")),
                )
            )
            legacy_workspace_id = result.inserted_primary_key[0]

        rows = connection.execute(
            select(
                products.c.id,
                products.c.public_id,
                products.c.workspace_id,
                products.c.collector_key_hash,
            ).where(
                (products.c.public_id.is_(None))
                | (products.c.workspace_id.is_(None))
                | (products.c.collector_key_hash.is_(None))
            )
        ).all()
        for row in rows:
            connection.execute(
                products.update()
                .where(products.c.id == row.id)
                .values(
                    public_id=row.public_id or _new_public_id("prd"),
                    workspace_id=row.workspace_id or legacy_workspace_id,
                    collector_key_hash=(
                        row.collector_key_hash or _hash_key(_new_secret("col"))
                    ),
                )
            )
        connection.execute(
            products.update()
            .where(products.c.evidence_updated_at.is_(None))
            .values(evidence_updated_at=_utc_now())
        )


def _mapping(row):
    return dict(row._mapping) if row else None


def _decode_product(row):
    product = _mapping(row)
    if not product:
        return None
    product["critical_flow"] = json.loads(product.get("critical_flow") or "[]")
    product["product_context"] = json.loads(product.get("product_context") or "{}")
    return product


# --- Workspace CRUD ---

def create_workspace():
    public_id = _new_public_id("ws")
    workspace_key = _new_secret("wsk")
    with get_engine().begin() as connection:
        result = connection.execute(
            workspaces.insert().values(
                public_id=public_id,
                key_hash=_hash_key(workspace_key),
            )
        )
        workspace_id = result.inserted_primary_key[0]
    return {
        "id": workspace_id,
        "public_id": public_id,
        "workspace_key": workspace_key,
    }


def get_workspace_by_key(workspace_key):
    if not workspace_key or not isinstance(workspace_key, str):
        return None
    with get_engine().connect() as connection:
        row = connection.execute(
            select(workspaces).where(
                workspaces.c.key_hash == _hash_key(workspace_key)
            )
        ).first()
    return _mapping(row)


# --- Product CRUD ---

def create_product(
    url,
    product_type,
    core_action,
    user_id,
    workspace_id,
    critical_flow=None,
    product_context=None,
):
    public_id = _new_public_id("prd")
    collector_key = _new_secret("col")
    with get_engine().begin() as connection:
        result = connection.execute(
            products.insert().values(
                public_id=public_id,
                workspace_id=workspace_id,
                collector_key_hash=_hash_key(collector_key),
                critical_flow=json.dumps(critical_flow or []),
                product_context=json.dumps(product_context or {}),
                evidence_updated_at=_utc_now(),
                url=url,
                product_type=product_type,
                core_action=core_action,
                user_id=user_id,
            )
        )
        internal_id = result.inserted_primary_key[0]
    return {
        "id": internal_id,
        "public_id": public_id,
        "collector_key": collector_key,
    }


def get_product(product_id):
    condition = (
        products.c.id == product_id
        if isinstance(product_id, int)
        else products.c.public_id == product_id
    )
    with get_engine().connect() as connection:
        row = connection.execute(select(products).where(condition)).first()
    return _decode_product(row)


def get_owned_product(public_id, workspace_id):
    with get_engine().connect() as connection:
        row = connection.execute(
            select(products).where(
                products.c.public_id == public_id,
                products.c.workspace_id == workspace_id,
            )
        ).first()
    return _decode_product(row)


def list_products(workspace_id):
    with get_engine().connect() as connection:
        rows = connection.execute(
            select(products)
            .where(products.c.workspace_id == workspace_id)
            .order_by(products.c.created_at.desc(), products.c.id.desc())
        ).all()
    return [_decode_product(row) for row in rows]


def verify_collector_key(public_id, collector_key):
    if not collector_key:
        return None
    with get_engine().connect() as connection:
        row = connection.execute(
            select(products).where(
                products.c.public_id == public_id,
                products.c.collector_key_hash == _hash_key(collector_key),
            )
        ).first()
    return _decode_product(row)


def rotate_collector_key(product_id):
    collector_key = _new_secret("col")
    with get_engine().begin() as connection:
        connection.execute(
            products.update()
            .where(products.c.id == product_id)
            .values(collector_key_hash=_hash_key(collector_key))
        )
    return collector_key


def get_collector_status(product_id):
    with get_engine().connect() as connection:
        event_count = connection.execute(
            select(func.count(events.c.id)).where(events.c.product_id == product_id)
        ).scalar_one()
        last_event = connection.execute(
            select(events.c.timestamp)
            .where(events.c.product_id == product_id)
            .order_by(events.c.timestamp.desc())
            .limit(1)
        ).scalar_one_or_none()
    return {
        "verified": event_count > 0,
        "event_count": event_count,
        "last_event_at": last_event,
    }


def update_critical_flow(product_id, steps):
    with get_engine().begin() as connection:
        connection.execute(
            products.update()
            .where(products.c.id == product_id)
            .values(
                critical_flow=json.dumps(steps),
                evidence_updated_at=_utc_now(),
            )
        )


def update_product_context(product_id, context):
    with get_engine().begin() as connection:
        connection.execute(
            products.update()
            .where(products.c.id == product_id)
            .values(
                product_context=json.dumps(context),
                evidence_updated_at=_utc_now(),
            )
        )


# --- Events CRUD ---

def insert_events(product_id, event_models):
    count = 0
    with get_engine().begin() as connection:
        for event in event_models:
            if event.event_id:
                exists = connection.execute(
                    select(events.c.id).where(
                        events.c.product_id == product_id,
                        events.c.event_id == event.event_id,
                    )
                ).first()
                if exists:
                    continue
            connection.execute(
                events.insert().values(
                    product_id=product_id,
                    event_id=event.event_id,
                    schema_version=event.schema_version,
                    action=event.action,
                    user_id=event.user_id,
                    session_id=event.session_id,
                    timestamp=event.timestamp,
                    page_url=event.page_url,
                    properties=json.dumps(event.properties),
                )
            )
            count += 1
        if count:
            connection.execute(
                products.update()
                .where(products.c.id == product_id)
                .values(evidence_updated_at=_utc_now())
            )
    return count


def delete_events(product_id):
    with get_engine().begin() as connection:
        connection.execute(events.delete().where(events.c.product_id == product_id))


def get_events(product_id, since=None):
    query = select(events).where(events.c.product_id == product_id)
    if since:
        query = query.where(events.c.timestamp >= since)
    query = query.order_by(events.c.timestamp)
    with get_engine().connect() as connection:
        rows = connection.execute(query).all()
    return [_mapping(row) for row in rows]


# --- Audits CRUD ---

def save_audit(product_id, audit_data):
    with get_engine().begin() as connection:
        connection.execute(
            audits.insert().values(
                product_id=product_id,
                audit_json=json.dumps(audit_data),
            )
        )
        connection.execute(
            products.update()
            .where(products.c.id == product_id)
            .values(evidence_updated_at=_utc_now())
        )


def get_audit(product_id):
    with get_engine().connect() as connection:
        row = connection.execute(
            select(audits)
            .where(audits.c.product_id == product_id)
            .order_by(audits.c.id.desc())
            .limit(1)
        ).first()
    data = _mapping(row)
    if data:
        data["audit_json"] = json.loads(data["audit_json"])
    return data


# --- Decisions CRUD ---

def save_decision(product_id, decision):
    with get_engine().begin() as connection:
        latest = connection.execute(
            select(func.coalesce(func.max(decisions.c.version), 0)).where(
                decisions.c.product_id == product_id
            )
        ).scalar_one()
        version = latest + 1
        result = connection.execute(
            decisions.insert().values(
                product_id=product_id,
                version=version,
                decision_json=json.dumps(decision),
            )
        )
        decision_id = result.inserted_primary_key[0]
    return decision_id, version


def get_latest_decision(product_id):
    with get_engine().connect() as connection:
        row = connection.execute(
            select(decisions)
            .where(decisions.c.product_id == product_id)
            .order_by(decisions.c.version.desc())
            .limit(1)
        ).first()
    stored = _mapping(row)
    if not stored:
        return None
    return {
        **json.loads(stored["decision_json"]),
        "decision_id": stored["id"],
        "version": stored["version"],
    }


def get_decision_freshness(product, decision):
    evidence_updated_at = product.get("evidence_updated_at")
    generated_at = decision.get("created_at")
    stale = bool(
        evidence_updated_at
        and generated_at
        and evidence_updated_at > generated_at
    )
    return {
        "stale": stale,
        "stale_reasons": (
            ["New evidence arrived after this decision was generated"]
            if stale
            else []
        ),
        "evidence_updated_at": evidence_updated_at,
    }


def get_decision(product_id, decision_id):
    with get_engine().connect() as connection:
        row = connection.execute(
            select(decisions).where(
                decisions.c.product_id == product_id,
                decisions.c.id == decision_id,
            )
        ).first()
    stored = _mapping(row)
    if not stored:
        return None
    return {
        **json.loads(stored["decision_json"]),
        "decision_id": stored["id"],
        "version": stored["version"],
    }


# --- Experiments CRUD ---

def create_experiment(product_id, decision_id, name, hypothesis, target_metric, baseline_value):
    public_id = _new_public_id("exp")
    with get_engine().begin() as connection:
        result = connection.execute(
            experiments.insert().values(
                public_id=public_id,
                product_id=product_id,
                decision_id=decision_id,
                name=name,
                hypothesis=hypothesis,
                target_metric=target_metric,
                baseline_value=baseline_value,
                status="planned",
            )
        )
        internal_id = result.inserted_primary_key[0]
    return get_experiment_by_internal_id(internal_id)


def get_experiment_for_decision(product_id, decision_id):
    with get_engine().connect() as connection:
        row = connection.execute(
            select(experiments)
            .where(
                experiments.c.product_id == product_id,
                experiments.c.decision_id == decision_id,
            )
            .order_by(experiments.c.id.desc())
            .limit(1)
        ).first()
    return _decode_experiment(row)


def _decode_experiment(row):
    experiment = _mapping(row)
    if not experiment:
        return None
    experiment["result"] = (
        json.loads(experiment["result_json"])
        if experiment.get("result_json")
        else None
    )
    return experiment


def get_experiment_by_internal_id(experiment_id):
    with get_engine().connect() as connection:
        row = connection.execute(
            select(experiments).where(experiments.c.id == experiment_id)
        ).first()
    return _decode_experiment(row)


def get_owned_experiment(public_id, workspace_id):
    with get_engine().connect() as connection:
        row = connection.execute(
            select(experiments)
            .join(products, experiments.c.product_id == products.c.id)
            .where(
                experiments.c.public_id == public_id,
                products.c.workspace_id == workspace_id,
            )
        ).first()
    return _decode_experiment(row)


def list_experiments(product_id):
    with get_engine().connect() as connection:
        rows = connection.execute(
            select(experiments)
            .where(experiments.c.product_id == product_id)
            .order_by(experiments.c.id.desc())
        ).all()
    return [_decode_experiment(row) for row in rows]


def mark_experiment_shipped(experiment_id, shipped_at):
    with get_engine().begin() as connection:
        connection.execute(
            experiments.update()
            .where(experiments.c.id == experiment_id)
            .values(status="collecting", shipped_at=shipped_at)
        )
    return get_experiment_by_internal_id(experiment_id)


def save_experiment_result(experiment_id, status, result):
    with get_engine().begin() as connection:
        product_id = connection.execute(
            select(experiments.c.product_id).where(
                experiments.c.id == experiment_id
            )
        ).scalar_one()
        connection.execute(
            experiments.update()
            .where(experiments.c.id == experiment_id)
            .values(status=status, result_json=json.dumps(result))
        )
        connection.execute(
            products.update()
            .where(products.c.id == product_id)
            .values(evidence_updated_at=_utc_now())
        )
    return get_experiment_by_internal_id(experiment_id)


# --- Insights CRUD ---

def save_insight(product_id, summary, actions):
    with get_engine().begin() as connection:
        connection.execute(
            insights.insert().values(
                product_id=product_id,
                summary=summary,
                actions=json.dumps(actions),
            )
        )


def get_latest_insight(product_id):
    with get_engine().connect() as connection:
        row = connection.execute(
            select(insights)
            .where(insights.c.product_id == product_id)
            .order_by(insights.c.id.desc())
            .limit(1)
        ).first()
    return _mapping(row)


# --- Chat history CRUD ---

def save_chat_message(product_id, user_id, role, content):
    with get_engine().begin() as connection:
        connection.execute(
            chat_history.insert().values(
                product_id=product_id,
                user_id=user_id,
                role=role,
                content=content,
            )
        )


def get_chat_history(product_id, user_id, limit=20):
    with get_engine().connect() as connection:
        rows = connection.execute(
            select(chat_history)
            .where(
                chat_history.c.product_id == product_id,
                chat_history.c.user_id == user_id,
            )
            .order_by(chat_history.c.id.asc())
            .limit(limit)
        ).all()
    return [_mapping(row) for row in rows]
