"""Opérations sur les événements de sécurité détectés par la surveillance caméra."""

from __future__ import annotations

from dogari.storage.database import db_session
from dogari.storage.models import SecurityEvent


def create_security_event(
    kind: str,
    severity: str,
    message: str | None,
    camera_source: str | None,
) -> SecurityEvent:
    """Journalise un événement de sécurité (foule, arme) détecté sur un flux caméra."""
    with db_session() as connection:
        cursor = connection.execute(
            """
            INSERT INTO security_events (kind, severity, message, camera_source)
            VALUES (?, ?, ?, ?)
            """,
            (kind, severity, message, camera_source),
        )
        event_id = cursor.lastrowid
        row = connection.execute("SELECT * FROM security_events WHERE id = ?", (event_id,)).fetchone()
    return SecurityEvent.from_row(row)


def get_recent_security_events(limit: int = 50) -> list[SecurityEvent]:
    """Retourne les événements de sécurité les plus récents."""
    with db_session() as connection:
        rows = connection.execute(
            "SELECT * FROM security_events ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [SecurityEvent.from_row(row) for row in rows]
