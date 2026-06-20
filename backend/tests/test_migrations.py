import sqlite3

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from shipsense import db


def test_legacy_sqlite_schema_is_migrated(tmp_path, monkeypatch):
    path = tmp_path / "legacy.db"
    connection = sqlite3.connect(path)
    connection.executescript("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            product_type TEXT NOT NULL,
            core_action TEXT NOT NULL,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            user_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        INSERT INTO products (url, product_type, core_action, user_id)
        VALUES ('https://legacy.example', 'b2b', 'signup', 'owner');
    """)
    connection.commit()
    connection.close()

    monkeypatch.setattr(db, "DB_PATH", str(path))
    db.init_db()

    migrated = db.get_product(1)
    assert migrated["public_id"].startswith("prd_")
    assert migrated["workspace_id"] is not None
    assert migrated["collector_key_hash"] is not None
    assert migrated["critical_flow"] == []
    assert migrated["product_context"] == {}


def test_schema_compiles_for_postgresql():
    dialect = postgresql.dialect()
    for table in db.metadata.sorted_tables:
        statement = str(CreateTable(table).compile(dialect=dialect))
        assert "CREATE TABLE" in statement
