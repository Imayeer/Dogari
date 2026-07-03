"""Modèles de données pour les utilisateurs et les journaux d'accès."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

import numpy as np

from dogari.core.constants import AccessStatus, UserStatus


def encode_embedding(embedding: np.ndarray) -> bytes:
    """Sérialise un embedding facial (vecteur numpy) en BLOB pour SQLite."""
    return embedding.astype(np.float64).tobytes()


def decode_embedding(blob: bytes | None) -> np.ndarray | None:
    """Désérialise un BLOB SQLite en vecteur numpy d'embedding facial."""
    if blob is None:
        return None
    return np.frombuffer(blob, dtype=np.float64)


@dataclass
class User:
    """Représente un utilisateur autorisé enregistré dans le système."""

    id: int | None
    full_name: str
    role: str | None
    status: str
    face_image_path: str | None
    face_embedding: bytes | None
    created_at: str | None

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE.value

    @property
    def embedding(self) -> np.ndarray | None:
        return decode_embedding(self.face_embedding)

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "User":
        return cls(
            id=row["id"],
            full_name=row["full_name"],
            role=row["role"],
            status=row["status"],
            face_image_path=row["face_image_path"],
            face_embedding=row["face_embedding"],
            created_at=row["created_at"],
        )


@dataclass
class AccessLog:
    """Représente une tentative d'accès journalisée."""

    id: int | None
    user_id: int | None
    full_name: str | None
    status: str
    similarity_score: float | None
    camera_source: str | None
    message: str | None
    created_at: str | None

    @property
    def is_granted(self) -> bool:
        return self.status == AccessStatus.GRANTED.value

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "AccessLog":
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            full_name=row["full_name"],
            status=row["status"],
            similarity_score=row["similarity_score"],
            camera_source=row["camera_source"],
            message=row["message"],
            created_at=row["created_at"],
        )
