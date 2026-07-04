"""Gestion de la connexion et du schéma de la base SQLite locale."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from dogari.core.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    role TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    face_image_path TEXT,
    face_embedding BLOB,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS access_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    full_name TEXT,
    status TEXT NOT NULL,
    similarity_score REAL,
    camera_source TEXT,
    message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS person_sightings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_id TEXT NOT NULL,
    user_id INTEGER,
    full_name TEXT,
    camera_source TEXT,
    similarity_score REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS security_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT,
    camera_source TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_access_logs_created_at ON access_logs (created_at);
CREATE INDEX IF NOT EXISTS idx_users_status ON users (status);
CREATE INDEX IF NOT EXISTS idx_person_sightings_search_id ON person_sightings (search_id);
CREATE INDEX IF NOT EXISTS idx_security_events_created_at ON security_events (created_at);
"""


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Ouvre une connexion SQLite avec les lignes accessibles par nom de colonne."""
    path = db_path or settings.database_path
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(db_path: Path | None = None) -> None:
    """Crée les tables de la base de données si elles n'existent pas encore."""
    with get_connection(db_path) as connection:
        connection.executescript(SCHEMA)


@contextmanager
def db_session(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    """Fournit une connexion SQLite dans un context manager avec commit/rollback."""
    connection = get_connection(db_path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
