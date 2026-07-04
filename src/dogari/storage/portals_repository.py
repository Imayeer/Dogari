"""Opérations CRUD sur la table `portals` (points d'accès physiques)."""

from __future__ import annotations

from dogari.core.constants import UserStatus
from dogari.core.exceptions import DogariError
from dogari.storage.database import db_session
from dogari.storage.models import Portal


def create_portal(
    name: str,
    camera_source: str,
    camera_kind: str = "usb",
    door_type: str = "simulated",
    gpio_relay_pin: int | None = None,
) -> Portal:
    """Crée un nouveau portail (point d'accès) avec sa caméra et son type de porte."""
    with db_session() as connection:
        cursor = connection.execute(
            """
            INSERT INTO portals (name, camera_source, camera_kind, door_type, gpio_relay_pin)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, camera_source, camera_kind, door_type, gpio_relay_pin),
        )
        portal_id = cursor.lastrowid
        row = connection.execute("SELECT * FROM portals WHERE id = ?", (portal_id,)).fetchone()
    return Portal.from_row(row)


def get_portal_by_id(portal_id: int) -> Portal:
    """Récupère un portail par son identifiant, lève DogariError sinon."""
    with db_session() as connection:
        row = connection.execute("SELECT * FROM portals WHERE id = ?", (portal_id,)).fetchone()
    if row is None:
        raise DogariError(f"Aucun portail avec l'id {portal_id}")
    return Portal.from_row(row)


def get_all_portals(include_inactive: bool = True) -> list[Portal]:
    """Retourne la liste des portails, actifs uniquement si demandé."""
    query = "SELECT * FROM portals"
    params: tuple = ()
    if not include_inactive:
        query += " WHERE status = ?"
        params = (UserStatus.ACTIVE.value,)
    query += " ORDER BY name"
    with db_session() as connection:
        rows = connection.execute(query, params).fetchall()
    return [Portal.from_row(row) for row in rows]


def update_portal(
    portal_id: int,
    name: str | None = None,
    camera_source: str | None = None,
    camera_kind: str | None = None,
    door_type: str | None = None,
    gpio_relay_pin: int | None = None,
    status: str | None = None,
) -> Portal:
    """Met à jour les champs fournis d'un portail existant."""
    current = get_portal_by_id(portal_id)
    updated = {
        "name": name if name is not None else current.name,
        "camera_source": camera_source if camera_source is not None else current.camera_source,
        "camera_kind": camera_kind if camera_kind is not None else current.camera_kind,
        "door_type": door_type if door_type is not None else current.door_type,
        "gpio_relay_pin": gpio_relay_pin if gpio_relay_pin is not None else current.gpio_relay_pin,
        "status": status if status is not None else current.status,
    }
    with db_session() as connection:
        connection.execute(
            """
            UPDATE portals
            SET name = ?, camera_source = ?, camera_kind = ?, door_type = ?, gpio_relay_pin = ?, status = ?
            WHERE id = ?
            """,
            (*updated.values(), portal_id),
        )
    return get_portal_by_id(portal_id)


def delete_portal(portal_id: int) -> None:
    """Supprime définitivement un portail."""
    get_portal_by_id(portal_id)  # lève DogariError si absent
    with db_session() as connection:
        connection.execute("DELETE FROM portals WHERE id = ?", (portal_id,))
