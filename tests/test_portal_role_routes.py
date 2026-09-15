"""Tests des routes CRUD portails, caméras IP, rôles et horaires."""

from __future__ import annotations

from fastapi.testclient import TestClient

from dogari.storage.users_repository import create_user


def test_portal_crud_lifecycle(temp_settings):
    from dogari.web.app import app

    with TestClient(app) as client:
        response = client.post(
            "/api/portals",
            json={"name": "Portail A", "camera_source": "0", "camera_kind": "usb", "door_type": "simulated"},
        )
        assert response.status_code == 201
        portal_id = response.json()["id"]

        response = client.get("/api/portals")
        assert response.status_code == 200
        assert any(p["id"] == portal_id for p in response.json())

        response = client.patch(f"/api/portals/{portal_id}", json={"door_type": "gpio", "gpio_relay_pin": 27})
        assert response.status_code == 200
        assert response.json()["door_type"] == "gpio"
        assert response.json()["gpio_relay_pin"] == 27

        response = client.delete(f"/api/portals/{portal_id}")
        assert response.status_code == 204

        response = client.patch(f"/api/portals/{portal_id}", json={"name": "x"})
        assert response.status_code == 404


def test_ip_camera_crud_lifecycle(temp_settings):
    from dogari.web.app import app

    with TestClient(app) as client:
        response = client.post("/api/ip-cameras", json={"name": "Parking", "source": "rtsp://cam.local/1"})
        assert response.status_code == 201
        camera_id = response.json()["id"]

        response = client.get("/api/ip-cameras")
        assert response.status_code == 200
        assert any(c["id"] == camera_id for c in response.json())

        response = client.delete(f"/api/ip-cameras/{camera_id}")
        assert response.status_code == 204

        response = client.delete(f"/api/ip-cameras/{camera_id}")
        assert response.status_code == 404


def test_role_and_schedule_lifecycle(temp_settings):
    from dogari.web.app import app

    with TestClient(app) as client:
        portal_response = client.post("/api/portals", json={"name": "Portail B", "camera_source": "0"})
        portal_id = portal_response.json()["id"]

        role_response = client.post("/api/roles", json={"name": "Employé"})
        assert role_response.status_code == 201
        role_id = role_response.json()["id"]

        schedule_response = client.post(
            f"/api/roles/{role_id}/schedules",
            json={"portal_id": portal_id, "weekday": 0, "start_time": "08:00", "end_time": "18:00"},
        )
        assert schedule_response.status_code == 201
        schedule_id = schedule_response.json()["id"]
        assert schedule_response.json()["start_time"] == "08:00:00"

        response = client.get(f"/api/roles/{role_id}/schedules")
        assert response.status_code == 200
        assert len(response.json()) == 1

        response = client.delete(f"/api/roles/{role_id}/schedules/{schedule_id}")
        assert response.status_code == 204
        assert client.get(f"/api/roles/{role_id}/schedules").json() == []


def test_delete_role_blocked_when_in_use(temp_settings):
    from dogari.web.app import app

    with TestClient(app) as client:
        role_response = client.post("/api/roles", json={"name": "Visiteur"})
        role_id = role_response.json()["id"]

        create_user(full_name="Test User", role_id=role_id)

        response = client.delete(f"/api/roles/{role_id}")
        assert response.status_code == 409


def test_delete_unknown_role_returns_404(temp_settings):
    from dogari.web.app import app

    with TestClient(app) as client:
        response = client.delete("/api/roles/999")
        assert response.status_code == 404


def test_revoke_portal_access_removes_schedules(temp_settings):
    from dogari.web.app import app

    with TestClient(app) as client:
        portal_id = client.post("/api/portals", json={"name": "Portail C", "camera_source": "0"}).json()["id"]
        role_id = client.post("/api/roles", json={"name": "Stagiaire"}).json()["id"]
        client.post(
            f"/api/roles/{role_id}/schedules",
            json={"portal_id": portal_id, "weekday": 1, "start_time": "09:00", "end_time": "17:00"},
        )

        response = client.delete(f"/api/roles/{role_id}/portals/{portal_id}")
        assert response.status_code == 204
        assert client.get(f"/api/roles/{role_id}/schedules").json() == []
