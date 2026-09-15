"""Tests de la route de reconnaissance /api/access/recognize (sélection par portail)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from dogari.access.controller import AccessAttemptResult
from dogari.core.constants import AccessStatus, RecognitionStatus
from dogari.storage.models import AccessLog
from dogari.storage.portals_repository import create_portal


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
            portal_id=None,
            portal_name=None,
            message="",
            created_at="2026-01-01 00:00:00",
        ),
    )


def test_recognize_returns_404_for_unknown_portal(temp_settings):
    from dogari.web.app import app

    with TestClient(app) as client:
        response = client.post("/api/access/recognize", params={"portal_id": 999})

    assert response.status_code == 404


def test_recognize_uses_given_portal(temp_settings, monkeypatch):
    import dogari.web.routes.access as access_routes
    from dogari.web.app import app

    portal = create_portal(name="Portail test", camera_source="0")

    captured = {}

    class FakeController:
        def __init__(self, portal_id, door_controller=None):
            captured["portal_id"] = portal_id

        def attempt_access(self):
            return _fake_result()

    monkeypatch.setattr(access_routes, "AccessController", FakeController)

    with TestClient(app) as client:
        response = client.post("/api/access/recognize", params={"portal_id": portal.id})

    assert response.status_code == 200
    assert captured["portal_id"] == portal.id
