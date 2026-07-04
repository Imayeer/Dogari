"""Route de statut système."""

from __future__ import annotations

from fastapi import APIRouter

from dogari import __version__
from dogari.core.config import settings
from dogari.storage.access_logs_repository import get_recent_logs
from dogari.storage.users_repository import get_all_users
from dogari.web.schemas import SystemStatusOut

router = APIRouter(prefix="/api/status", tags=["status"])


@router.get("", response_model=SystemStatusOut)
def get_status() -> SystemStatusOut:
    """Retourne un aperçu de l'état du système : base de données, utilisateurs, accès."""
    users = get_all_users()
    recent_logs = get_recent_logs(limit=1000)
    return SystemStatusOut(
        version=__version__,
        database_ok=True,
        users_count=len(users),
        active_users_count=len([user for user in users if user.is_active]),
        recent_access_count=len(recent_logs),
        door_mode="gpio" if settings.use_gpio else "simulated",
        camera_source=str(settings.camera_source),
        secondary_camera_source=(
            str(settings.secondary_camera_source) if settings.secondary_camera_source is not None else None
        ),
    )
