import sqlite3
import os
from datetime import datetime

DB_PATH = os.getenv("DATABASE_URL", "./shipsense.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            product_type TEXT NOT NULL,
            core_action TEXT NOT NULL,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            user_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            summary TEXT NOT NULL,
            actions TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE INDEX IF NOT EXISTS idx_events_product ON events(product_id);
        CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
        CREATE INDEX IF NOT EXISTS idx_chat_product ON chat_history(product_id);
    """)
    conn.commit()
    conn.close()


# --- Product CRUD ---

def create_product(url, product_type, core_action, user_id):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO products (url, product_type, core_action, user_id) VALUES (?, ?, ?, ?)",
        (url, product_type, core_action, user_id),
    )
    product_id = cur.lastrowid
    conn.commit()
    conn.close()
    return product_id


def get_product(product_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# --- Events CRUD ---

def insert_events(product_id, events):
    conn = get_connection()
    count = 0
    for ev in events:
        conn.execute(
            "INSERT INTO events (product_id, action, user_id, timestamp) VALUES (?, ?, ?, ?)",
            (product_id, ev.action, ev.user_id, ev.timestamp),
        )
        count += 1
    conn.commit()
    conn.close()
    return count


def get_events(product_id, since=None):
    conn = get_connection()
    if since:
        rows = conn.execute(
            "SELECT * FROM events WHERE product_id = ? AND timestamp >= ? ORDER BY timestamp",
            (product_id, since),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM events WHERE product_id = ? ORDER BY timestamp", (product_id,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Insights CRUD ---

def save_insight(product_id, summary, actions):
    import json
    conn = get_connection()
    conn.execute(
        "INSERT INTO insights (product_id, summary, actions) VALUES (?, ?, ?)",
        (product_id, summary, json.dumps(actions)),
    )
    conn.commit()
    conn.close()


def get_latest_insight(product_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM insights WHERE product_id = ? ORDER BY created_at DESC LIMIT 1",
        (product_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# --- Chat history CRUD ---

def save_chat_message(product_id, user_id, role, content):
    conn = get_connection()
    conn.execute(
        "INSERT INTO chat_history (product_id, user_id, role, content) VALUES (?, ?, ?, ?)",
        (product_id, user_id, role, content),
    )
    conn.commit()
    conn.close()


def get_chat_history(product_id, user_id, limit=20):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM chat_history WHERE product_id = ? AND user_id = ? ORDER BY created_at ASC LIMIT ?",
        (product_id, user_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
