"""Schémas Pydantic exposés par l'API web de Dogari."""

from __future__ import annotations

from pydantic import BaseModel

from dogari.storage.models import AccessLog, User


class UserOut(BaseModel):
    id: int
    full_name: str
    role: str | None
    status: str
    face_image_path: str | None
    created_at: str | None

    @classmethod
    def from_user(cls, user: User) -> "UserOut":
        return cls(
            id=user.id,
            full_name=user.full_name,
            role=user.role,
            status=user.status,
            face_image_path=user.face_image_path,
            created_at=user.created_at,
        )


class AccessLogOut(BaseModel):
    id: int
    user_id: int | None
    full_name: str | None
    status: str
    similarity_score: float | None
    camera_source: str | None
    message: str | None
    created_at: str | None

    @classmethod
    def from_log(cls, log: AccessLog) -> "AccessLogOut":
        return cls(
            id=log.id,
            user_id=log.user_id,
            full_name=log.full_name,
            status=log.status,
            similarity_score=log.similarity_score,
            camera_source=log.camera_source,
            message=log.message,
            created_at=log.created_at,
        )


class AccessAttemptOut(BaseModel):
    access_status: str
    recognition_status: str
    user_id: int | None
    full_name: str | None
    similarity_score: float | None
    message: str
    log_id: int | None


class SystemStatusOut(BaseModel):
    version: str
    database_ok: bool
    users_count: int
    active_users_count: int
    recent_access_count: int
    door_mode: str
    camera_source: str
