"""Routes CRUD pour les portails (points d'accès physiques)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from dogari.core.exceptions import DogariError
from dogari.storage.portals_repository import (
    create_portal,
    delete_portal,
    get_all_portals,
    update_portal,
)
from dogari.web.schemas import PortalOut

router = APIRouter(prefix="/api/portals", tags=["portals"])


class PortalIn(BaseModel):
    name: str
    camera_source: str
    camera_kind: Literal["usb", "ip"] = "usb"
    door_type: Literal["simulated", "gpio"] = "simulated"
    gpio_relay_pin: int | None = None


class PortalUpdateIn(BaseModel):
    name: str | None = None
    camera_source: str | None = None
    camera_kind: Literal["usb", "ip"] | None = None
    door_type: Literal["simulated", "gpio"] | None = None
    gpio_relay_pin: int | None = None
    status: Literal["active", "inactive"] | None = None


@router.get("", response_model=list[PortalOut])
def list_portals() -> list[PortalOut]:
    """Liste tous les portails (points d'accès), actifs et inactifs."""
    return [PortalOut.from_portal(portal) for portal in get_all_portals()]


@router.post("", response_model=PortalOut, status_code=201)
def add_portal(payload: PortalIn) -> PortalOut:
    """Crée un nouveau portail (point d'accès physique)."""
    portal = create_portal(
        name=payload.name,
        camera_source=payload.camera_source,
        camera_kind=payload.camera_kind,
        door_type=payload.door_type,
        gpio_relay_pin=payload.gpio_relay_pin,
    )
    return PortalOut.from_portal(portal)


@router.patch("/{portal_id}", response_model=PortalOut)
def edit_portal(portal_id: int, payload: PortalUpdateIn) -> PortalOut:
    """Met à jour un portail existant."""
    try:
        portal = update_portal(portal_id, **payload.model_dump(exclude_unset=True))
    except DogariError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PortalOut.from_portal(portal)


@router.delete("/{portal_id}", status_code=204, response_model=None)
def remove_portal(portal_id: int) -> None:
    """Supprime définitivement un portail."""
    try:
        delete_portal(portal_id)
    except DogariError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
