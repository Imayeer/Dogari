"""Routes CRUD pour les caméras IP de surveillance (pas des portails : pas de porte)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from dogari.core.exceptions import DogariError
from dogari.storage.ip_cameras_repository import create_ip_camera, delete_ip_camera, get_all_ip_cameras
from dogari.web.schemas import IPCameraOut

router = APIRouter(prefix="/api/ip-cameras", tags=["ip-cameras"])


class IPCameraIn(BaseModel):
    name: str
    source: str


@router.get("", response_model=list[IPCameraOut])
def list_ip_cameras() -> list[IPCameraOut]:
    """Liste toutes les caméras IP de surveillance."""
    return [IPCameraOut.from_ip_camera(camera) for camera in get_all_ip_cameras()]


@router.post("", response_model=IPCameraOut, status_code=201)
def add_ip_camera(payload: IPCameraIn) -> IPCameraOut:
    """Ajoute une nouvelle caméra IP de surveillance."""
    camera = create_ip_camera(name=payload.name, source=payload.source)
    return IPCameraOut.from_ip_camera(camera)


@router.delete("/{camera_id}", status_code=204, response_model=None)
def remove_ip_camera(camera_id: int) -> None:
    """Supprime définitivement une caméra IP."""
    try:
        delete_ip_camera(camera_id)
    except DogariError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
