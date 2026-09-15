"""Routes de recherche continue d'une personne nommée sur un flux caméra."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from dogari.access.person_search import (
    get_search,
    list_active_searches,
    start_search,
    stop_search,
)
from dogari.core.exceptions import DogariError
from dogari.storage.sightings_repository import get_sightings
from dogari.web.camera_resolution import resolve_camera_source
from dogari.web.schemas import PersonSearchOut, PersonSightingOut

router = APIRouter(prefix="/api/search", tags=["search"])


class StartSearchIn(BaseModel):
    full_name: str
    portal_id: int | None = None
    ip_camera_id: int | None = None


@router.post("/start", response_model=PersonSearchOut, status_code=201)
def start(payload: StartSearchIn) -> PersonSearchOut:
    """Démarre une surveillance continue pour retrouver un utilisateur nommé (sur un portail ou une caméra IP)."""
    camera_source = resolve_camera_source(payload.portal_id, payload.ip_camera_id)

    try:
        search = start_search(payload.full_name, camera_source)
    except DogariError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PersonSearchOut.from_search(search)


@router.post("/{search_id}/stop")
def stop(search_id: str) -> dict:
    """Arrête une recherche continue en cours."""
    try:
        stop_search(search_id)
    except DogariError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"stopped": True}


@router.get("", response_model=list[PersonSearchOut])
def list_searches() -> list[PersonSearchOut]:
    """Retourne les recherches actuellement en cours d'exécution."""
    return [PersonSearchOut.from_search(search) for search in list_active_searches()]


@router.get("/{search_id}", response_model=PersonSearchOut)
def get(search_id: str) -> PersonSearchOut:
    """Retourne l'état d'une recherche (active ou arrêtée) par son identifiant."""
    try:
        search = get_search(search_id)
    except DogariError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PersonSearchOut.from_search(search)


@router.get("/{search_id}/sightings", response_model=list[PersonSightingOut])
def sightings(search_id: str, limit: int = 50) -> list[PersonSightingOut]:
    """Retourne les observations journalisées pour une recherche donnée."""
    return [PersonSightingOut.from_sighting(sighting) for sighting in get_sightings(search_id, limit=limit)]
