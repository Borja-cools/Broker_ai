"""Kleine SQLite-laag met expliciete migratie en geparameteriseerde queries."""

import hashlib
import json
from pathlib import Path
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4


SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS users(
 id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, token_hash TEXT NOT NULL,
 role TEXT NOT NULL CHECK(role IN ('admin','viewer')), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS bots(
 id TEXT PRIMARY KEY, name TEXT UNIQUE NOT NULL, specialization TEXT NOT NULL,
 approval_mode TEXT NOT NULL CHECK(approval_mode IN ('manual','automatic_limited','disabled')),
 status TEXT NOT NULL CHECK(status IN ('active','paused')),
 max_auto_order_value TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS portfolio_snapshots(
 id TEXT PRIMARY KEY, cash_balance TEXT NOT NULL, total_equity TEXT NOT NULL,
 currency TEXT NOT NULL, observed_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS analyses(
 id TEXT PRIMARY KEY, bot_id TEXT NOT NULL REFERENCES bots(id), symbol TEXT NOT NULL,
 summary TEXT NOT NULL, confidence TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS order_proposals(
 id TEXT PRIMARY KEY, bot_id TEXT NOT NULL REFERENCES bots(id), symbol TEXT NOT NULL,
 side TEXT NOT NULL CHECK(side IN ('buy','sell')), quantity TEXT NOT NULL,
 price TEXT NOT NULL, rationale TEXT NOT NULL, status TEXT NOT NULL,
 created_at TEXT NOT NULL, reviewed_at TEXT);
CREATE TABLE IF NOT EXISTS audit_logs(
 id TEXT PRIMARY KEY, event_type TEXT NOT NULL, actor_id TEXT, entity_id TEXT,
 details_json TEXT NOT NULL, created_at TEXT NOT NULL);
INSERT OR IGNORE INTO schema_migrations(version) VALUES(1);
"""


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._memory_connection: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        if self.path == ":memory:":
            if self._memory_connection is None:
                self._memory_connection = sqlite3.connect(":memory:", check_same_thread=False)
                self._configure(self._memory_connection)
            return self._memory_connection
        connection = sqlite3.connect(self.path, timeout=5)
        self._configure(connection)
        return connection

    @staticmethod
    def _configure(connection: sqlite3.Connection) -> None:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")

    def migrate(self) -> None:
        connection = self.connect()
        connection.executescript(SCHEMA)
        connection.commit()
        if self.path != ":memory:":
            connection.close()

    def execute(self, sql: str, parameters: tuple = ()) -> sqlite3.Cursor:
        connection = self.connect()
        cursor = connection.execute(sql, parameters)
        connection.commit()
        if self.path != ":memory:":
            connection.close()
        return cursor

    def fetchone(self, sql: str, parameters: tuple = ()) -> dict | None:
        connection = self.connect()
        row = connection.execute(sql, parameters).fetchone()
        if self.path != ":memory:":
            connection.close()
        return dict(row) if row else None

    def fetchall(self, sql: str, parameters: tuple = ()) -> list[dict]:
        connection = self.connect()
        rows = connection.execute(sql, parameters).fetchall()
        if self.path != ":memory:":
            connection.close()
        return [dict(row) for row in rows]

    def seed_admin(self, token: str) -> dict:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        existing = self.fetchone("SELECT * FROM users WHERE username = ?", ("local-admin",))
        if existing:
            self.execute(
                "UPDATE users SET token_hash = ? WHERE id = ?",
                (token_hash, existing["id"]),
            )
            return self.fetchone("SELECT * FROM users WHERE id = ?", (existing["id"],))
        user_id = str(uuid4())
        now = _now()
        self.execute(
            "INSERT INTO users VALUES(?,?,?,?,?)",
            (user_id, "local-admin", token_hash, "admin", now),
        )
        return self.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))

    def audit(self, event_type: str, actor_id: str | None, entity_id: str | None, details: dict) -> None:
        self.execute(
            "INSERT INTO audit_logs VALUES(?,?,?,?,?,?)",
            (str(uuid4()), event_type, actor_id, entity_id, json.dumps(details), _now()),
        )

    def healthy(self) -> bool:
        return self.fetchone("SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1") is not None

    def backup(self, destination: str | Path) -> Path:
        """Maak via SQLite zelf een consistente lokale back-up."""

        if self.path == ":memory:":
            raise ValueError("Een in-memorydatabase kan niet naar dit back-uppad.")
        target_path = Path(destination)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        source = sqlite3.connect(self.path)
        target = sqlite3.connect(target_path)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        return target_path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
