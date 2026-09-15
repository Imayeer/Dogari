"""Tests de la vérification d'accès rôle/portail/horaire (access/role_access.py)."""

from __future__ import annotations

from datetime import datetime

from dogari.access.role_access import is_role_authorized_for_portal
from dogari.storage.portals_repository import create_portal
from dogari.storage.role_schedules_repository import add_schedule
from dogari.storage.roles_repository import create_role


def test_no_role_is_never_authorized(temp_settings):
    portal = create_portal(name="Portail", camera_source="0")

    result = is_role_authorized_for_portal(None, portal.id)

    assert result.authorized is False


def test_role_with_no_schedule_is_denied(temp_settings):
    role = create_role(name="Sans accès")
    portal = create_portal(name="Portail", camera_source="0")

    result = is_role_authorized_for_portal(role.id, portal.id)

    assert result.authorized is False


def test_role_authorized_within_scheduled_window(temp_settings):
    role = create_role(name="Employé")
    portal = create_portal(name="Portail", camera_source="0")
    # Lundi (weekday=0), 08:00-18:00
    add_schedule(role.id, portal.id, weekday=0, start_time="08:00", end_time="18:00")

    monday_at_noon = datetime(2026, 1, 5, 12, 0)  # 5 janvier 2026 est un lundi
    assert monday_at_noon.weekday() == 0

    result = is_role_authorized_for_portal(role.id, portal.id, now=monday_at_noon)

    assert result.authorized is True


def test_role_denied_outside_scheduled_hours(temp_settings):
    role = create_role(name="Employé")
    portal = create_portal(name="Portail", camera_source="0")
    add_schedule(role.id, portal.id, weekday=0, start_time="08:00", end_time="18:00")

    monday_at_night = datetime(2026, 1, 5, 22, 0)

    result = is_role_authorized_for_portal(role.id, portal.id, now=monday_at_night)

    assert result.authorized is False


def test_role_denied_on_unscheduled_weekday(temp_settings):
    role = create_role(name="Employé")
    portal = create_portal(name="Portail", camera_source="0")
    add_schedule(role.id, portal.id, weekday=0, start_time="08:00", end_time="18:00")  # lundi seulement

    saturday = datetime(2026, 1, 10, 12, 0)  # 10 janvier 2026 est un samedi
    assert saturday.weekday() == 5

    result = is_role_authorized_for_portal(role.id, portal.id, now=saturday)

    assert result.authorized is False


def test_role_authorized_for_one_portal_but_not_another(temp_settings):
    role = create_role(name="Employé")
    portal_a = create_portal(name="Portail A", camera_source="0")
    portal_b = create_portal(name="Portail B", camera_source="1")
    add_schedule(role.id, portal_a.id, weekday=0, start_time="08:00", end_time="18:00")

    monday_at_noon = datetime(2026, 1, 5, 12, 0)

    assert is_role_authorized_for_portal(role.id, portal_a.id, now=monday_at_noon).authorized is True
    assert is_role_authorized_for_portal(role.id, portal_b.id, now=monday_at_noon).authorized is False
