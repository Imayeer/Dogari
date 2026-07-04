"""Tests de la sélection de caméra (principale/secondaire) pour la reconnaissance."""

from __future__ import annotations

from dataclasses import replace

from fastapi.testclient import TestClient

from dogari.access.controller import AccessAttemptResult
from dogari.core.constants import AccessStatus, RecognitionStatus
from dogari.storage.models import AccessLog


def _fake_result() -> AccessAttemptResult:
    return AccessAttemptResult(
        access_status=AccessStatus.DENIED,
        recognition_status=RecognitionStatus.NO_FACE_DETECTED,
        user=None,
        similarity_score=None,
        message="Aucun visage détecté dans l'image capturée.",
        log=AccessLog(
            id=1,
            user_id=None,
            full_name=None,
            status=AccessStatus.DENIED.value,
            similarity_score=None,
            camera_source="0",
            message="",
            created_at="2026-01-01 00:00:00",
        ),
    )


def test_recognize_rejects_secondary_camera_when_not_configured(temp_settings, monkeypatch):
    import dogari.web.routes.access as access_routes
    from dogari.web.app import app

    monkeypatch.setattr(access_routes, "settings", replace(temp_settings, secondary_camera_source=None))

    with TestClient(app) as client:
        response = client.post("/api/access/recognize", params={"camera": "secondary"})

    assert response.status_code == 400


def test_recognize_uses_secondary_camera_source_when_configured(temp_settings, monkeypatch):
    import dogari.web.routes.access as access_routes
    from dogari.web.app import app

    monkeypatch.setattr(
        access_routes, "settings", replace(temp_settings, secondary_camera_source="rtsp://camera2.local/stream")
    )

    captured = {}

    class FakeController:
        def __init__(self, camera_source=None, **kwargs):
            captured["camera_source"] = camera_source

        def attempt_access(self):
            return _fake_result()

    monkeypatch.setattr(access_routes, "AccessController", FakeController)

    with TestClient(app) as client:
        response = client.post("/api/access/recognize", params={"camera": "secondary"})

    assert response.status_code == 200
    assert captured["camera_source"] == "rtsp://camera2.local/stream"


def test_recognize_uses_primary_camera_by_default(temp_settings, monkeypatch):
    import dogari.web.routes.access as access_routes
    from dogari.web.app import app

    monkeypatch.setattr(access_routes, "settings", temp_settings)

    captured = {}

    class FakeController:
        def __init__(self, camera_source=None, **kwargs):
            captured["camera_source"] = camera_source

        def attempt_access(self):
            return _fake_result()

    monkeypatch.setattr(access_routes, "AccessController", FakeController)

    with TestClient(app) as client:
        response = client.post("/api/access/recognize")

    assert response.status_code == 200
    assert captured["camera_source"] is None
