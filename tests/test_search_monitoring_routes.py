"""Tests des routes web de recherche de personne et de surveillance sécurité."""

from __future__ import annotations

import time
from dataclasses import replace
from unittest import mock

import numpy as np
from fastapi.testclient import TestClient

from dogari.access import camera_watcher as camera_watcher_module
from dogari.access import person_search as person_search_module
from dogari.access import security_monitor as security_monitor_module
from dogari.storage.portals_repository import create_portal
from dogari.storage.users_repository import create_user


def _fake_camera() -> mock.MagicMock:
    camera = mock.MagicMock()
    camera.__enter__ = mock.Mock(return_value=camera)
    camera.__exit__ = mock.Mock(return_value=False)
    camera.capture_frame = mock.Mock(return_value=np.zeros((5, 5, 3), dtype=np.uint8))
    return camera


def _wait_until(predicate, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("Condition non atteinte avant le délai imparti")


def test_search_route_full_lifecycle(temp_settings, monkeypatch):
    portal = create_portal(name="Portail recherche", camera_source="0")
    embedding = np.zeros(128)
    create_user(full_name="Yara", face_embedding=embedding)

    monkeypatch.setattr(camera_watcher_module, "Camera", lambda source=None: _fake_camera())
    monkeypatch.setattr(person_search_module, "detect_single_face", lambda frame: np.array([0, 0, 10, 10]))
    monkeypatch.setattr(person_search_module, "generate_embedding", lambda frame, face: embedding.copy())
    monkeypatch.setattr(
        person_search_module,
        "settings",
        replace(temp_settings, search_poll_interval_seconds=0.01, search_sighting_cooldown_seconds=0.0),
    )

    from dogari.web.app import app

    with TestClient(app) as client:
        response = client.post("/api/search/start", json={"full_name": "Yara", "portal_id": portal.id})
        assert response.status_code == 201
        search_id = response.json()["search_id"]

        response = client.get("/api/search")
        assert response.status_code == 200
        assert any(s["search_id"] == search_id for s in response.json())

        _wait_until(lambda: client.get(f"/api/search/{search_id}/sightings").json())

        sightings = client.get(f"/api/search/{search_id}/sightings").json()
        assert len(sightings) >= 1
        assert sightings[0]["full_name"] == "Yara"

        response = client.post(f"/api/search/{search_id}/stop")
        assert response.status_code == 200
        assert response.json() == {"stopped": True}


def test_search_route_returns_400_without_camera_selector(temp_settings):
    from dogari.web.app import app

    with TestClient(app) as client:
        response = client.post("/api/search/start", json={"full_name": "Personne Inconnue"})

    assert response.status_code == 400


def test_search_route_returns_404_for_unknown_user(temp_settings):
    portal = create_portal(name="Portail recherche 2", camera_source="0")

    from dogari.web.app import app

    with TestClient(app) as client:
        response = client.post(
            "/api/search/start", json={"full_name": "Personne Inconnue", "portal_id": portal.id}
        )

    assert response.status_code == 404


def test_monitoring_route_full_lifecycle(temp_settings, monkeypatch):
    portal = create_portal(name="Portail surveillance", camera_source="0")

    monkeypatch.setattr(camera_watcher_module, "Camera", lambda source=None: _fake_camera())
    monkeypatch.setattr(security_monitor_module, "detect_faces", lambda frame: [object()] * 7)
    monkeypatch.setattr(
        security_monitor_module,
        "settings",
        replace(temp_settings, monitoring_poll_interval_seconds=0.01, crowd_size_threshold=5),
    )

    from dogari.web.app import app

    with TestClient(app) as client:
        response = client.post("/api/monitoring/start", json={"portal_id": portal.id})
        assert response.status_code == 201
        monitor_id = response.json()["monitor_id"]

        response = client.get("/api/monitoring")
        assert response.status_code == 200
        assert any(m["monitor_id"] == monitor_id for m in response.json())

        _wait_until(lambda: client.get("/api/monitoring/events").json())

        events = client.get("/api/monitoring/events").json()
        assert events[0]["kind"] == "crowd_detected"

        response = client.post(f"/api/monitoring/{monitor_id}/stop")
        assert response.status_code == 200
