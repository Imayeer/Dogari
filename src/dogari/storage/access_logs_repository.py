"""Opérations CRUD sur la table `access_logs`."""

from __future__ import annotations

from dogari.storage.database import db_session
from dogari.storage.models import AccessLog


def create_log(
    status: str,
    user_id: int | None = None,
    full_name: str | None = None,
    similarity_score: float | None = None,
    camera_source: str | None = None,
    message: str | None = None,
) -> AccessLog:
    """Enregistre une tentative d'accès dans la base de données."""
    with db_session() as connection:
        cursor = connection.execute(
            """
            INSERT INTO access_logs (user_id, full_name, status, similarity_score, camera_source, message)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, full_name, status, similarity_score, camera_source, message),
        )
        log_id = cursor.lastrowid
        row = connection.execute("SELECT * FROM access_logs WHERE id = ?", (log_id,)).fetchone()
    return AccessLog.from_row(row)


def get_recent_logs(limit: int = 50) -> list[AccessLog]:
    """Retourne les tentatives d'accès les plus récentes, du plus récent au plus ancien."""
    with db_session() as connection:
        rows = connection.execute(
            "SELECT * FROM access_logs ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [AccessLog.from_row(row) for row in rows]


def get_logs_for_user(user_id: int, limit: int = 50) -> list[AccessLog]:
    """Retourne l'historique d'accès d'un utilisateur donné."""
    with db_session() as connection:
        rows = connection.execute(
            "SELECT * FROM access_logs WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [AccessLog.from_row(row) for row in rows]
