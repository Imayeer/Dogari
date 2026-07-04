"""Opérations CRUD sur `role_portal_schedules` (horaires d'accès d'un rôle à un portail)."""

from __future__ import annotations

from dogari.storage.database import db_session
from dogari.storage.models import RolePortalSchedule


def add_schedule(role_id: int, portal_id: int, weekday: int, start_time: str, end_time: str) -> RolePortalSchedule:
    """Ajoute une plage horaire d'accès pour un rôle sur un portail, un jour de semaine donné."""
    with db_session() as connection:
        cursor = connection.execute(
            """
            INSERT INTO role_portal_schedules (role_id, portal_id, weekday, start_time, end_time)
            VALUES (?, ?, ?, ?, ?)
            """,
            (role_id, portal_id, weekday, start_time, end_time),
        )
        schedule_id = cursor.lastrowid
        row = connection.execute(
            "SELECT * FROM role_portal_schedules WHERE id = ?", (schedule_id,)
        ).fetchone()
    return RolePortalSchedule.from_row(row)


def get_schedules_for_role(role_id: int) -> list[RolePortalSchedule]:
    """Retourne tous les horaires d'accès configurés pour un rôle (tous portails confondus)."""
    with db_session() as connection:
        rows = connection.execute(
            "SELECT * FROM role_portal_schedules WHERE role_id = ? ORDER BY portal_id, weekday, start_time",
            (role_id,),
        ).fetchall()
    return [RolePortalSchedule.from_row(row) for row in rows]


def get_schedules_for_role_and_portal(role_id: int, portal_id: int) -> list[RolePortalSchedule]:
    """Retourne les horaires d'accès d'un rôle pour un portail donné."""
    with db_session() as connection:
        rows = connection.execute(
            "SELECT * FROM role_portal_schedules WHERE role_id = ? AND portal_id = ?",
            (role_id, portal_id),
        ).fetchall()
    return [RolePortalSchedule.from_row(row) for row in rows]


def delete_schedule(schedule_id: int) -> None:
    """Supprime une plage horaire d'accès."""
    with db_session() as connection:
        connection.execute("DELETE FROM role_portal_schedules WHERE id = ?", (schedule_id,))


def delete_schedules_for_role_and_portal(role_id: int, portal_id: int) -> None:
    """Supprime tous les horaires d'un rôle pour un portail donné (retire l'accès à ce portail)."""
    with db_session() as connection:
        connection.execute(
            "DELETE FROM role_portal_schedules WHERE role_id = ? AND portal_id = ?",
            (role_id, portal_id),
        )
