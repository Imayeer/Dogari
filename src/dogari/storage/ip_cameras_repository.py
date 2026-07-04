"""Opérations CRUD sur la table `ip_cameras` (caméras de surveillance, sans porte)."""

from __future__ import annotations

from dogari.core.constants import UserStatus
from dogari.core.exceptions import DogariError
from dogari.storage.database import db_session
from dogari.storage.models import IPCamera


def create_ip_camera(name: str, source: str) -> IPCamera:
    """Crée une nouvelle caméra IP de surveillance."""
    with db_session() as connection:
        cursor = connection.execute(
            "INSERT INTO ip_cameras (name, source) VALUES (?, ?)",
            (name, source),
        )
        camera_id = cursor.lastrowid
        row = connection.execute("SELECT * FROM ip_cameras WHERE id = ?", (camera_id,)).fetchone()
    return IPCamera.from_row(row)


def get_ip_camera_by_id(camera_id: int) -> IPCamera:
    """Récupère une caméra IP par son identifiant, lève DogariError sinon."""
    with db_session() as connection:
        row = connection.execute("SELECT * FROM ip_cameras WHERE id = ?", (camera_id,)).fetchone()
    if row is None:
        raise DogariError(f"Aucune caméra IP avec l'id {camera_id}")
    return IPCamera.from_row(row)


def get_all_ip_cameras(include_inactive: bool = True) -> list[IPCamera]:
    """Retourne la liste des caméras IP, actives uniquement si demandé."""
    query = "SELECT * FROM ip_cameras"
    params: tuple = ()
    if not include_inactive:
        query += " WHERE status = ?"
        params = (UserStatus.ACTIVE.value,)
    query += " ORDER BY name"
    with db_session() as connection:
        rows = connection.execute(query, params).fetchall()
    return [IPCamera.from_row(row) for row in rows]


def delete_ip_camera(camera_id: int) -> None:
    """Supprime définitivement une caméra IP."""
    get_ip_camera_by_id(camera_id)  # lève DogariError si absente
    with db_session() as connection:
        connection.execute("DELETE FROM ip_cameras WHERE id = ?", (camera_id,))
