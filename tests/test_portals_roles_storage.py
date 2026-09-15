"""Tests du stockage des portails, caméras IP, rôles et horaires d'accès."""

from __future__ import annotations

import pytest

from dogari.core.exceptions import DogariError
from dogari.storage import (
    ip_cameras_repository,
    portals_repository,
    role_schedules_repository,
    roles_repository,
)
from dogari.storage.seed import seed_defaults
from dogari.storage.users_repository import create_user, get_user_by_id


def test_create_and_get_portal(temp_settings):
    portal = portals_repository.create_portal(
        name="Entrée principale", camera_source="0", camera_kind="usb", door_type="simulated"
    )

    fetched = portals_repository.get_portal_by_id(portal.id)

    assert fetched.name == "Entrée principale"
    assert fetched.camera_kind == "usb"
    assert fetched.door_type == "simulated"
    assert fetched.is_active is True


def test_update_and_delete_portal(temp_settings):
    portal = portals_repository.create_portal(name="Portail Nord", camera_source="0")

    updated = portals_repository.update_portal(portal.id, door_type="gpio", gpio_relay_pin=22)
    assert updated.door_type == "gpio"
    assert updated.gpio_relay_pin == 22

    portals_repository.delete_portal(portal.id)
    with pytest.raises(DogariError):
        portals_repository.get_portal_by_id(portal.id)


def test_create_and_list_ip_cameras(temp_settings):
    ip_cameras_repository.create_ip_camera(name="Parking", source="rtsp://cam1.local/stream")

    cameras = ip_cameras_repository.get_all_ip_cameras()

    assert len(cameras) == 1
    assert cameras[0].name == "Parking"


def test_create_role_and_schedule_then_delete_role_blocked_if_in_use(temp_settings):
    role = roles_repository.create_role(name="Professeur")
    portal = portals_repository.create_portal(name="Salle A", camera_source="0")

    role_schedules_repository.add_schedule(role.id, portal.id, weekday=0, start_time="08:00", end_time="18:00")
    schedules = role_schedules_repository.get_schedules_for_role_and_portal(role.id, portal.id)
    assert len(schedules) == 1

    create_user(full_name="Sami", role_id=role.id)

    with pytest.raises(DogariError):
        roles_repository.delete_role(role.id)


def test_delete_role_cascades_schedules_when_not_in_use(temp_settings):
    role = roles_repository.create_role(name="Visiteur")
    portal = portals_repository.create_portal(name="Salle B", camera_source="0")
    role_schedules_repository.add_schedule(role.id, portal.id, weekday=1, start_time="09:00", end_time="17:00")

    roles_repository.delete_role(role.id)

    assert role_schedules_repository.get_schedules_for_role(role.id) == []


def test_user_role_join_returns_role_name(temp_settings):
    role = roles_repository.create_role(name="Étudiant")
    user = create_user(full_name="Fatou", role_id=role.id)

    fetched = get_user_by_id(user.id)

    assert fetched.role_id == role.id
    assert fetched.role_name == "Étudiant"


def test_seed_defaults_creates_default_portal(temp_settings):
    seed_defaults()

    portals = portals_repository.get_all_portals()

    assert len(portals) == 1
    assert portals[0].name == "Portail principal"


def test_seed_defaults_is_idempotent(temp_settings):
    seed_defaults()
    seed_defaults()

    assert len(portals_repository.get_all_portals()) == 1
