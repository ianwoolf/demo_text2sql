from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from app.models import SemanticContext


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: Path):
        self.path = path

    def connect(self):
        connection = sqlite3.connect(self.path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self):
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS spaces (id TEXT PRIMARY KEY, name TEXT, description TEXT, provider_type TEXT, metadata_path TEXT, target_type TEXT, instructions TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS conversations (id TEXT PRIMARY KEY, space_id TEXT, title TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, conversation_id TEXT, role TEXT, content TEXT, payload TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS feedback (id TEXT PRIMARY KEY, message_id TEXT, rating TEXT, comment TEXT, status TEXT, created_at TEXT);
            CREATE TABLE IF NOT EXISTS semantics (space_id TEXT PRIMARY KEY, payload TEXT);
            CREATE TABLE IF NOT EXISTS transformation_requests (id TEXT PRIMARY KEY, name TEXT, status TEXT, stage TEXT, version INTEGER, snapshot TEXT, created_by TEXT, created_at TEXT, updated_at TEXT);
            """)

    def seed_demo(self, metadata_path: Path):
        semantics = SemanticContext(
            instructions=["Sales includes completed orders only", "Use calendar years and USD by default"],
            terms=[{"name": "Active customer", "definition": "A customer with a completed order in the last 90 days"}],
            metrics=[{"name": "Sales", "expression": "SUM(orders.amount)", "description": "Tax-inclusive amount for completed orders"}],
            joins=[{"name": "Order to customer", "expression": "orders.customer_id = customers.customer_id"}],
            examples=[{"question": "Show monthly sales this year", "sql": "SELECT DATE_FORMAT(order_date, '%Y-%m') AS month, SUM(amount) AS sales FROM orders WHERE status = 'completed' GROUP BY month ORDER BY month LIMIT 200", "trusted": True}],
        )
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM spaces WHERE id='sales-demo'").fetchone():
                db.execute("INSERT INTO spaces VALUES (?,?,?,?,?,?,?,?)", ("sales-demo", "Sales Analytics", "Explore orders, customers, regions, and products with natural language", "local", str(metadata_path), "mock", json.dumps(semantics.instructions, ensure_ascii=False), now()))
            db.execute(
                "UPDATE spaces SET name=?, description=?, provider_type=?, metadata_path=?, target_type=?, instructions=? WHERE id='sales-demo'",
                ("Sales Analytics", "Explore orders, customers, regions, and products with natural language", "local", str(metadata_path), "mock", json.dumps(semantics.instructions, ensure_ascii=False)),
            )
            db.execute(
                "INSERT INTO semantics VALUES (?,?) ON CONFLICT(space_id) DO UPDATE SET payload=excluded.payload",
                ("sales-demo", semantics.model_dump_json()),
            )

    def rows(self, sql: str, params=()):
        with self.connect() as db:
            return [dict(row) for row in db.execute(sql, params).fetchall()]

    def one(self, sql: str, params=()):
        with self.connect() as db:
            row = db.execute(sql, params).fetchone()
            return dict(row) if row else None

    def execute(self, sql: str, params=()):
        with self.connect() as db:
            db.execute(sql, params)

    def create_conversation(self, space_id: str, title: str = "New conversation"):
        item = {"id": str(uuid4()), "space_id": space_id, "title": title, "created_at": now()}
        self.execute("INSERT INTO conversations VALUES (?,?,?,?)", tuple(item.values()))
        return item

    def add_message(self, conversation_id: str, role: str, content: str, payload: dict | None = None):
        item = {"id": str(uuid4()), "conversation_id": conversation_id, "role": role, "content": content, "payload": json.dumps(payload or {}, ensure_ascii=False), "created_at": now()}
        self.execute("INSERT INTO messages VALUES (?,?,?,?,?,?)", tuple(item.values()))
        return item
