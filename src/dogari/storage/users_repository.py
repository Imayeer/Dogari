"""Opérations CRUD sur la table `users`."""

from __future__ import annotations

import sqlite3

import numpy as np

from dogari.core.constants import UserStatus
from dogari.core.exceptions import UserNotFoundError
from dogari.storage.database import db_session
from dogari.storage.models import User, encode_embedding


def create_user(
    full_name: str,
    role: str | None = None,
    face_image_path: str | None = None,
    face_embedding: np.ndarray | None = None,
    status: str = UserStatus.ACTIVE.value,
) -> User:
    """Ajoute un nouvel utilisateur autorisé dans la base de données."""
    embedding_blob = encode_embedding(face_embedding) if face_embedding is not None else None
    with db_session() as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (full_name, role, status, face_image_path, face_embedding)
            VALUES (?, ?, ?, ?, ?)
            """,
            (full_name, role, status, face_image_path, embedding_blob),
        )
        user_id = cursor.lastrowid
        row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return User.from_row(row)


def get_user_by_id(user_id: int) -> User:
    """Récupère un utilisateur par son identifiant, lève UserNotFoundError sinon."""
    with db_session() as connection:
        row = connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise UserNotFoundError(f"Aucun utilisateur avec l'id {user_id}")
    return User.from_row(row)


def get_all_users(include_inactive: bool = True) -> list[User]:
    """Retourne la liste des utilisateurs, actifs uniquement si demandé."""
    query = "SELECT * FROM users"
    params: tuple = ()
    if not include_inactive:
        query += " WHERE status = ?"
        params = (UserStatus.ACTIVE.value,)
    query += " ORDER BY full_name"
    with db_session() as connection:
        rows = connection.execute(query, params).fetchall()
    return [User.from_row(row) for row in rows]


def get_active_users_with_embeddings() -> list[User]:
    """Retourne les utilisateurs actifs disposant d'un embedding facial exploitable."""
    return [
        user
        for user in get_all_users(include_inactive=False)
        if user.face_embedding is not None
    ]


def update_user(
    user_id: int,
    full_name: str | None = None,
    role: str | None = None,
    status: str | None = None,
    face_image_path: str | None = None,
    face_embedding: np.ndarray | None = None,
) -> User:
    """Met à jour les champs fournis d'un utilisateur existant."""
    current = get_user_by_id(user_id)
    updated = {
        "full_name": full_name if full_name is not None else current.full_name,
        "role": role if role is not None else current.role,
        "status": status if status is not None else current.status,
        "face_image_path": face_image_path if face_image_path is not None else current.face_image_path,
        "face_embedding": (
            encode_embedding(face_embedding) if face_embedding is not None else current.face_embedding
        ),
    }
    with db_session() as connection:
        connection.execute(
            """
            UPDATE users
            SET full_name = ?, role = ?, status = ?, face_image_path = ?, face_embedding = ?
            WHERE id = ?
            """,
            (*updated.values(), user_id),
        )
    return get_user_by_id(user_id)


def deactivate_user(user_id: int) -> User:
    """Désactive un utilisateur sans supprimer son historique d'accès."""
    return update_user(user_id, status=UserStatus.INACTIVE.value)


def delete_user(user_id: int) -> None:
    """Supprime définitivement un utilisateur de la base de données."""
    get_user_by_id(user_id)  # lève UserNotFoundError si absent
    with db_session() as connection:
        connection.execute("DELETE FROM users WHERE id = ?", (user_id,))
