"""Routes de surveillance sécurité continue (foule, armes) sur un flux caméra."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from dogari.access.security_monitor import list_active_monitors, start_monitoring, stop_monitoring
from dogari.core.exceptions import DogariError
from dogari.storage.security_events_repository import get_recent_security_events
from dogari.web.camera_resolution import resolve_camera_source
from dogari.web.schemas import SecurityEventOut, SecurityMonitorOut

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


class StartMonitoringIn(BaseModel):
    portal_id: int | None = None
    ip_camera_id: int | None = None


@router.post("/start", response_model=SecurityMonitorOut, status_code=201)
def start(payload: StartMonitoringIn) -> SecurityMonitorOut:
    """Démarre une surveillance sécurité continue (foule, armes) sur un portail ou une caméra IP."""
    camera_source = resolve_camera_source(payload.portal_id, payload.ip_camera_id)
    monitor = start_monitoring(camera_source)
    return SecurityMonitorOut.from_monitor(monitor)


@router.post("/{monitor_id}/stop")
def stop(monitor_id: str) -> dict:
    """Arrête une surveillance sécurité en cours."""
    try:
        stop_monitoring(monitor_id)
    except DogariError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"stopped": True}


@router.get("", response_model=list[SecurityMonitorOut])
def list_monitors() -> list[SecurityMonitorOut]:
    """Retourne les surveillances actuellement en cours d'exécution."""
    return [SecurityMonitorOut.from_monitor(monitor) for monitor in list_active_monitors()]


@router.get("/events", response_model=list[SecurityEventOut])
def events(limit: int = 50) -> list[SecurityEventOut]:
    """Retourne les événements de sécurité (foule, armes) les plus récents."""
    return [SecurityEventOut.from_event(event) for event in get_recent_security_events(limit=limit)]
