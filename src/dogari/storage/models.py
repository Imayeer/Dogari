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
    role_id: int | None
    role_name: str | None
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
            role_id=row["role_id"],
            role_name=row["role_name"],
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


@dataclass
class PersonSighting:
    """Représente une observation d'une personne recherchée sur un flux caméra."""

    id: int | None
    search_id: str
    user_id: int | None
    full_name: str | None
    camera_source: str | None
    similarity_score: float | None
    created_at: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "PersonSighting":
        return cls(
            id=row["id"],
            search_id=row["search_id"],
            user_id=row["user_id"],
            full_name=row["full_name"],
            camera_source=row["camera_source"],
            similarity_score=row["similarity_score"],
            created_at=row["created_at"],
        )


@dataclass
class SecurityEvent:
    """Représente un événement de sécurité détecté par la surveillance caméra (foule, arme)."""

    id: int | None
    kind: str
    severity: str
    message: str | None
    camera_source: str | None
    created_at: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "SecurityEvent":
        return cls(
            id=row["id"],
            kind=row["kind"],
            severity=row["severity"],
            message=row["message"],
            camera_source=row["camera_source"],
            created_at=row["created_at"],
        )


@dataclass
class Portal:
    """Représente un point d'accès physique (porte) contrôlé par une caméra dédiée."""

    id: int | None
    name: str
    camera_source: str
    camera_kind: str
    door_type: str
    gpio_relay_pin: int | None
    status: str
    created_at: str | None

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE.value

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Portal":
        return cls(
            id=row["id"],
            name=row["name"],
            camera_source=row["camera_source"],
            camera_kind=row["camera_kind"],
            door_type=row["door_type"],
            gpio_relay_pin=row["gpio_relay_pin"],
            status=row["status"],
            created_at=row["created_at"],
        )


@dataclass
class IPCamera:
    """Représente une caméra IP de surveillance (pas un point d'accès : pas de porte)."""

    id: int | None
    name: str
    source: str
    status: str
    created_at: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "IPCamera":
        return cls(
            id=row["id"],
            name=row["name"],
            source=row["source"],
            status=row["status"],
            created_at=row["created_at"],
        )


@dataclass
class Role:
    """Représente un rôle d'accès (regroupe les portails autorisés et leurs horaires)."""

    id: int | None
    name: str
    created_at: str | None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Role":
        return cls(id=row["id"], name=row["name"], created_at=row["created_at"])


@dataclass
class RolePortalSchedule:
    """Représente une plage horaire, pour un jour de semaine donné, où un rôle a accès à un portail.

    `weekday` suit la convention `datetime.weekday()` : 0 = lundi ... 6 = dimanche.
    `start_time`/`end_time` sont au format "HH:MM".
    """

    id: int | None
    role_id: int
    portal_id: int
    weekday: int
    start_time: str
    end_time: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "RolePortalSchedule":
        return cls(
            id=row["id"],
            role_id=row["role_id"],
            portal_id=row["portal_id"],
            weekday=row["weekday"],
            start_time=row["start_time"],
            end_time=row["end_time"],
        )
