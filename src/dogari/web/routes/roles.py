"""Routes CRUD pour les rôles d'accès et leurs horaires par portail."""

from __future__ import annotations

from datetime import time as dt_time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from dogari.core.exceptions import DogariError
from dogari.storage.role_schedules_repository import (
    add_schedule,
    delete_schedule,
    delete_schedules_for_role_and_portal,
    get_all_schedules,
    get_schedules_for_role,
)
from dogari.storage.roles_repository import create_role, delete_role, get_all_roles, get_role_by_id
from dogari.web.schemas import RoleOut, RolePortalScheduleOut

router = APIRouter(prefix="/api/roles", tags=["roles"])


class RoleIn(BaseModel):
    name: str


class ScheduleIn(BaseModel):
    portal_id: int
    weekday: int = Field(ge=0, le=6, description="0 = lundi ... 6 = dimanche")
    start_time: dt_time
    end_time: dt_time


@router.get("", response_model=list[RoleOut])
def list_roles() -> list[RoleOut]:
    """Liste tous les rôles d'accès."""
    return [RoleOut.from_role(role) for role in get_all_roles()]


@router.post("", response_model=RoleOut, status_code=201)
def add_role(payload: RoleIn) -> RoleOut:
    """Crée un nouveau rôle d'accès."""
    return RoleOut.from_role(create_role(name=payload.name))


@router.delete("/{role_id}", status_code=204, response_model=None)
def remove_role(role_id: int) -> None:
    """Supprime un rôle (refusé s'il est encore utilisé par des utilisateurs)."""
    try:
        get_role_by_id(role_id)
    except DogariError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        delete_role(role_id)
    except DogariError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/schedules", response_model=list[RolePortalScheduleOut])
def list_all_schedules() -> list[RolePortalScheduleOut]:
    """Liste tous les horaires d'accès, tous rôles et portails confondus."""
    return [RolePortalScheduleOut.from_schedule(schedule) for schedule in get_all_schedules()]


@router.get("/{role_id}/schedules", response_model=list[RolePortalScheduleOut])
def list_schedules(role_id: int) -> list[RolePortalScheduleOut]:
    """Liste les horaires d'accès configurés pour un rôle (tous portails confondus)."""
    return [RolePortalScheduleOut.from_schedule(schedule) for schedule in get_schedules_for_role(role_id)]


@router.post("/{role_id}/schedules", response_model=RolePortalScheduleOut, status_code=201)
def add_role_schedule(role_id: int, payload: ScheduleIn) -> RolePortalScheduleOut:
    """Ajoute une plage horaire d'accès pour ce rôle sur un portail donné."""
    schedule = add_schedule(
        role_id=role_id,
        portal_id=payload.portal_id,
        weekday=payload.weekday,
        start_time=payload.start_time.isoformat(),
        end_time=payload.end_time.isoformat(),
    )
    return RolePortalScheduleOut.from_schedule(schedule)


@router.delete("/{role_id}/schedules/{schedule_id}", status_code=204, response_model=None)
def remove_schedule(role_id: int, schedule_id: int) -> None:
    """Supprime une plage horaire d'accès."""
    delete_schedule(schedule_id)


@router.delete("/{role_id}/portals/{portal_id}", status_code=204, response_model=None)
def revoke_portal_access(role_id: int, portal_id: int) -> None:
    """Retire tout accès de ce rôle à ce portail (supprime tous ses horaires pour ce portail)."""
    delete_schedules_for_role_and_portal(role_id, portal_id)
