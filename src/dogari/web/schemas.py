"""Schémas Pydantic exposés par l'API web de Dogari."""

from __future__ import annotations

from pydantic import BaseModel

from dogari.access.anomaly import AnomalyEvent
from dogari.access.person_search import PersonSearch
from dogari.access.reports import AccessReport, DailyStats
from dogari.access.security_monitor import SecurityMonitor
from dogari.storage.models import (
    AccessLog,
    IPCamera,
    PersonSighting,
    Portal,
    Role,
    RolePortalSchedule,
    SecurityEvent,
    User,
)


class UserOut(BaseModel):
    id: int
    full_name: str
    role_id: int | None
    role_name: str | None
    status: str
    face_image_path: str | None
    created_at: str | None

    @classmethod
    def from_user(cls, user: User) -> "UserOut":
        return cls(
            id=user.id,
            full_name=user.full_name,
            role_id=user.role_id,
            role_name=user.role_name,
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
    portal_id: int | None
    portal_name: str | None
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
            portal_id=log.portal_id,
            portal_name=log.portal_name,
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


class AnomalyEventOut(BaseModel):
    kind: str
    severity: str
    message: str
    log_ids: list[int]

    @classmethod
    def from_event(cls, event: AnomalyEvent) -> "AnomalyEventOut":
        return cls(kind=event.kind, severity=event.severity, message=event.message, log_ids=event.log_ids)


class DailyStatsOut(BaseModel):
    date: str
    total: int
    granted: int
    denied: int
    error: int

    @classmethod
    def from_stats(cls, stats: DailyStats) -> "DailyStatsOut":
        return cls(date=stats.date, total=stats.total, granted=stats.granted, denied=stats.denied, error=stats.error)


class AccessReportOut(BaseModel):
    period_start: str
    period_end: str
    total_attempts: int
    granted: int
    denied: int
    error: int
    unique_users: list[str]
    daily_breakdown: list[DailyStatsOut]
    anomalies: list[AnomalyEventOut]

    @classmethod
    def from_report(cls, report: AccessReport) -> "AccessReportOut":
        return cls(
            period_start=report.period_start,
            period_end=report.period_end,
            total_attempts=report.total_attempts,
            granted=report.granted,
            denied=report.denied,
            error=report.error,
            unique_users=report.unique_users,
            daily_breakdown=[DailyStatsOut.from_stats(day) for day in report.daily_breakdown],
            anomalies=[AnomalyEventOut.from_event(event) for event in report.anomalies],
        )


class PersonSearchOut(BaseModel):
    search_id: str
    full_name: str
    camera_source: str
    started_at: str
    sightings_count: int
    is_running: bool
    last_error: str | None

    @classmethod
    def from_search(cls, search: PersonSearch) -> "PersonSearchOut":
        return cls(
            search_id=search.search_id,
            full_name=search.full_name,
            camera_source=str(search.camera_source),
            started_at=search.started_at,
            sightings_count=search.sightings_count,
            is_running=search.is_running,
            last_error=search.last_error,
        )


class PersonSightingOut(BaseModel):
    id: int
    search_id: str
    user_id: int | None
    full_name: str | None
    camera_source: str | None
    similarity_score: float | None
    created_at: str | None

    @classmethod
    def from_sighting(cls, sighting: PersonSighting) -> "PersonSightingOut":
        return cls(
            id=sighting.id,
            search_id=sighting.search_id,
            user_id=sighting.user_id,
            full_name=sighting.full_name,
            camera_source=sighting.camera_source,
            similarity_score=sighting.similarity_score,
            created_at=sighting.created_at,
        )


class SecurityMonitorOut(BaseModel):
    monitor_id: str
    camera_source: str
    started_at: str
    is_running: bool
    last_error: str | None

    @classmethod
    def from_monitor(cls, monitor: SecurityMonitor) -> "SecurityMonitorOut":
        return cls(
            monitor_id=monitor.monitor_id,
            camera_source=str(monitor.camera_source),
            started_at=monitor.started_at,
            is_running=monitor.is_running,
            last_error=monitor.last_error,
        )


class SecurityEventOut(BaseModel):
    id: int
    kind: str
    severity: str
    message: str | None
    camera_source: str | None
    created_at: str | None

    @classmethod
    def from_event(cls, event: SecurityEvent) -> "SecurityEventOut":
        return cls(
            id=event.id,
            kind=event.kind,
            severity=event.severity,
            message=event.message,
            camera_source=event.camera_source,
            created_at=event.created_at,
        )


class PortalOut(BaseModel):
    id: int
    name: str
    camera_source: str
    camera_kind: str
    door_type: str
    gpio_relay_pin: int | None
    status: str
    created_at: str | None

    @classmethod
    def from_portal(cls, portal: Portal) -> "PortalOut":
        return cls(
            id=portal.id,
            name=portal.name,
            camera_source=portal.camera_source,
            camera_kind=portal.camera_kind,
            door_type=portal.door_type,
            gpio_relay_pin=portal.gpio_relay_pin,
            status=portal.status,
            created_at=portal.created_at,
        )


class IPCameraOut(BaseModel):
    id: int
    name: str
    source: str
    status: str
    created_at: str | None

    @classmethod
    def from_ip_camera(cls, camera: IPCamera) -> "IPCameraOut":
        return cls(
            id=camera.id,
            name=camera.name,
            source=camera.source,
            status=camera.status,
            created_at=camera.created_at,
        )


class RoleOut(BaseModel):
    id: int
    name: str
    created_at: str | None

    @classmethod
    def from_role(cls, role: Role) -> "RoleOut":
        return cls(id=role.id, name=role.name, created_at=role.created_at)


class RolePortalScheduleOut(BaseModel):
    id: int
    role_id: int
    portal_id: int
    weekday: int
    start_time: str
    end_time: str

    @classmethod
    def from_schedule(cls, schedule: RolePortalSchedule) -> "RolePortalScheduleOut":
        return cls(
            id=schedule.id,
            role_id=schedule.role_id,
            portal_id=schedule.portal_id,
            weekday=schedule.weekday,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
        )


class SystemStatusOut(BaseModel):
    version: str
    database_ok: bool
    users_count: int
    active_users_count: int
    recent_access_count: int
    portals_count: int
    ip_cameras_count: int
    roles_count: int
