"""Opérations CRUD sur la table `access_logs`."""

from __future__ import annotations

from dogari.storage.database import db_session
from dogari.storage.models import AccessLog

_SELECT_LOG = """
    SELECT access_logs.*, portals.name AS portal_name
    FROM access_logs
    LEFT JOIN portals ON access_logs.portal_id = portals.id
"""


def create_log(
    status: str,
    user_id: int | None = None,
    full_name: str | None = None,
    similarity_score: float | None = None,
    camera_source: str | None = None,
    portal_id: int | None = None,
    message: str | None = None,
) -> AccessLog:
    """Enregistre une tentative d'accès dans la base de données."""
    with db_session() as connection:
        cursor = connection.execute(
            """
            INSERT INTO access_logs (user_id, full_name, status, similarity_score, camera_source, portal_id, message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, full_name, status, similarity_score, camera_source, portal_id, message),
        )
        log_id = cursor.lastrowid
        row = connection.execute(f"{_SELECT_LOG} WHERE access_logs.id = ?", (log_id,)).fetchone()
    return AccessLog.from_row(row)


def get_recent_logs(limit: int = 50) -> list[AccessLog]:
    """Retourne les tentatives d'accès les plus récentes, du plus récent au plus ancien."""
    with db_session() as connection:
        rows = connection.execute(
            f"{_SELECT_LOG} ORDER BY access_logs.created_at DESC, access_logs.id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [AccessLog.from_row(row) for row in rows]


def get_logs_between(start: str, end: str) -> list[AccessLog]:
    """Retourne les tentatives d'accès entre deux horodatages (inclus), triées chronologiquement."""
    with db_session() as connection:
        rows = connection.execute(
            f"{_SELECT_LOG} WHERE access_logs.created_at BETWEEN ? AND ? "
            "ORDER BY access_logs.created_at ASC, access_logs.id ASC",
            (start, end),
        ).fetchall()
    return [AccessLog.from_row(row) for row in rows]


def get_logs_for_user(user_id: int, limit: int = 50) -> list[AccessLog]:
    """Retourne l'historique d'accès d'un utilisateur donné."""
    with db_session() as connection:
        rows = connection.execute(
            f"{_SELECT_LOG} WHERE access_logs.user_id = ? "
            "ORDER BY access_logs.created_at DESC, access_logs.id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [AccessLog.from_row(row) for row in rows]
