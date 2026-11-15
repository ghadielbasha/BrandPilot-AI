"""SQLite connection and idempotent schema initialization."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 username TEXT NOT NULL UNIQUE COLLATE NOCASE,
 display_name TEXT NOT NULL,
 role TEXT NOT NULL CHECK(role IN ('ADMIN','EDITOR','REVIEWER')),
 password_hash TEXT NOT NULL,
 is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS campaigns (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 creator_user_id INTEGER NOT NULL REFERENCES users(id),
 brand TEXT NOT NULL CHECK(brand IN ('omsar','dawlati')),
 original_brief TEXT NOT NULL,
 objective TEXT NOT NULL,
 target_audience TEXT NOT NULL,
 platform TEXT NOT NULL,
 requested_languages TEXT NOT NULL,
 generated_strategy TEXT,
 generated_content TEXT,
 validation_results TEXT,
 normalization_changes TEXT,
 repair_metadata TEXT,
 status TEXT NOT NULL DEFAULT 'DRAFT' CHECK(status IN ('DRAFT','SUBMITTED_FOR_REVIEW','APPROVED','REJECTED')),
 version INTEGER NOT NULL DEFAULT 1,
 approved_version INTEGER,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 submitted_at TEXT,
 approved_at TEXT,
 approved_by INTEGER REFERENCES users(id),
 rejected_at TEXT,
 rejected_by INTEGER REFERENCES users(id),
 review_comment TEXT
);
CREATE TABLE IF NOT EXISTS campaign_versions (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
 version_number INTEGER NOT NULL,
 brief_snapshot TEXT NOT NULL,
 strategy_snapshot TEXT,
 content_snapshot TEXT,
 validation_snapshot TEXT,
 repair_metadata TEXT,
 created_by INTEGER NOT NULL REFERENCES users(id),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(campaign_id, version_number)
);
CREATE TABLE IF NOT EXISTS audit_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 actor_user_id INTEGER REFERENCES users(id),
 action TEXT NOT NULL,
 entity_type TEXT NOT NULL,
 entity_id TEXT,
 metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_campaign_status ON campaigns(status);
CREATE INDEX IF NOT EXISTS idx_campaign_creator ON campaigns(creator_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_events(entity_type, entity_id);
PRAGMA user_version = 1;
"""


class ClosingConnection(sqlite3.Connection):
    """Make context-managed read connections close as well as commit."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, factory=ClosingConnection)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def initialize_database(db_path: str | Path | None = None) -> None:
    with connect(db_path) as connection:
        connection.executescript(SCHEMA)


@contextmanager
def transaction(db_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    connection = connect(db_path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

