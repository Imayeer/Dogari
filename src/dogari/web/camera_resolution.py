"""Résolution d'une source caméra à partir d'un portail ou d'une caméra IP.

Partagée par les routes de recherche de personne et de surveillance sécurité,
qui peuvent cibler indifféremment un portail (point d'accès) ou une caméra IP
de surveillance (sans porte).
"""

from __future__ import annotations

from fastapi import HTTPException

from dogari.core.config import parse_camera_source
from dogari.core.exceptions import DogariError
from dogari.storage.ip_cameras_repository import get_ip_camera_by_id
from dogari.storage.portals_repository import get_portal_by_id


def resolve_camera_source(portal_id: int | None, ip_camera_id: int | None) -> int | str:
    """Résout `portal_id` ou `ip_camera_id` (exactement l'un des deux) vers une source caméra utilisable."""
    if portal_id is not None and ip_camera_id is not None:
        raise HTTPException(status_code=400, detail="Précisez portal_id ou ip_camera_id, pas les deux.")

    if portal_id is not None:
        try:
            portal = get_portal_by_id(portal_id)
        except DogariError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return parse_camera_source(portal.camera_source)

    if ip_camera_id is not None:
        try:
            camera = get_ip_camera_by_id(ip_camera_id)
        except DogariError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return parse_camera_source(camera.source)

    raise HTTPException(status_code=400, detail="Précisez portal_id ou ip_camera_id.")
