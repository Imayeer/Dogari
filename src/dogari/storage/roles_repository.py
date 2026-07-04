"""Opérations CRUD sur la table `roles` (rôles d'accès)."""

from __future__ import annotations

import sqlite3

from dogari.core.exceptions import DogariError
from dogari.storage.database import db_session
from dogari.storage.models import Role


def create_role(name: str) -> Role:
    """Crée un nouveau rôle d'accès."""
    with db_session() as connection:
        cursor = connection.execute("INSERT INTO roles (name) VALUES (?)", (name,))
        role_id = cursor.lastrowid
        row = connection.execute("SELECT * FROM roles WHERE id = ?", (role_id,)).fetchone()
    return Role.from_row(row)


def get_role_by_id(role_id: int) -> Role:
    """Récupère un rôle par son identifiant, lève DogariError sinon."""
    with db_session() as connection:
        row = connection.execute("SELECT * FROM roles WHERE id = ?", (role_id,)).fetchone()
    if row is None:
        raise DogariError(f"Aucun rôle avec l'id {role_id}")
    return Role.from_row(row)


def get_all_roles() -> list[Role]:
    """Retourne la liste de tous les rôles d'accès."""
    with db_session() as connection:
        rows = connection.execute("SELECT * FROM roles ORDER BY name").fetchall()
    return [Role.from_row(row) for row in rows]


def delete_role(role_id: int) -> None:
    """Supprime définitivement un rôle (et ses horaires associés, en cascade)."""
    get_role_by_id(role_id)  # lève DogariError si absent
    try:
        with db_session() as connection:
            connection.execute("DELETE FROM roles WHERE id = ?", (role_id,))
    except sqlite3.IntegrityError as exc:
        raise DogariError(
            "Impossible de supprimer ce rôle : des utilisateurs y sont encore rattachés. "
            "Réassignez-les d'abord à un autre rôle."
        ) from exc
