"""Tests de l'orchestration du contrôle d'accès (AccessController)."""

from __future__ import annotations

from unittest import mock

import numpy as np

from dogari.access import controller as controller_module
from dogari.access.controller import AccessController
from dogari.access.door import DoorController
from dogari.core.constants import AccessStatus, RecognitionStatus
from dogari.storage.users_repository import create_user

FACE = np.array([0, 0, 10, 10])


class FakeDoorController(DoorController):
    def __init__(self) -> None:
        self.opened = False

    def open_door(self, hold_seconds: float | None = None) -> None:
        self.opened = True

    def close_door(self) -> None:
        self.opened = False


def _dummy_frame() -> np.ndarray:
    return np.zeros((10, 10, 3), dtype=np.uint8)


def _fake_camera(burst_frames: list[np.ndarray]) -> mock.MagicMock:
    camera = mock.MagicMock()
    camera.__enter__ = mock.Mock(return_value=camera)
    camera.__exit__ = mock.Mock(return_value=False)
    camera.capture_burst = mock.Mock(return_value=burst_frames)
    return camera


def test_attempt_access_grants_known_user(temp_settings, monkeypatch):
    embedding = np.zeros(128)
    user = create_user(full_name="Ines", face_embedding=embedding)

    monkeypatch.setattr(controller_module, "detect_single_face", lambda frame: (0, 10, 10, 0))
    monkeypatch.setattr(controller_module, "generate_embedding", lambda frame, loc: embedding.copy())

    door = FakeDoorController()
    result = AccessController(door_controller=door).attempt_access(frame=_dummy_frame())

    assert result.access_status == AccessStatus.GRANTED
    assert result.recognition_status == RecognitionStatus.AUTHORIZED
    assert result.user.id == user.id
    assert door.opened is True
    assert result.log.status == AccessStatus.GRANTED.value


def test_attempt_access_denies_unknown_face(temp_settings, monkeypatch):
    known_embedding = np.zeros(128)
    create_user(full_name="Jack", face_embedding=known_embedding)

    monkeypatch.setattr(controller_module, "detect_single_face", lambda frame: (0, 10, 10, 0))
    monkeypatch.setattr(
        controller_module, "generate_embedding", lambda frame, loc: np.ones(128) * 10
    )

    door = FakeDoorController()
    result = AccessController(door_controller=door).attempt_access(frame=_dummy_frame())

    assert result.access_status == AccessStatus.DENIED
    assert result.recognition_status == RecognitionStatus.UNKNOWN
    assert result.user is None
    assert door.opened is False


def test_attempt_access_no_face_detected(temp_settings, monkeypatch):
    monkeypatch.setattr(controller_module, "detect_single_face", lambda frame: None)

    door = FakeDoorController()
    result = AccessController(door_controller=door).attempt_access(frame=_dummy_frame())

    assert result.access_status == AccessStatus.DENIED
    assert result.recognition_status == RecognitionStatus.NO_FACE_DETECTED
    assert door.opened is False


def test_attempt_access_denies_static_photo_as_spoof(temp_settings, monkeypatch):
    """Une rafale d'images identiques (photo statique) doit être bloquée par la vivacité."""
    embedding = np.zeros(128)
    create_user(full_name="Lina", face_embedding=embedding)

    identical_frames = [_dummy_frame() for _ in range(5)]

    monkeypatch.setattr(controller_module, "Camera", lambda source=None: _fake_camera(identical_frames))
    monkeypatch.setattr(controller_module, "detect_single_face", lambda frame: FACE)
    generate_embedding_mock = mock.Mock(return_value=embedding.copy())
    monkeypatch.setattr(controller_module, "generate_embedding", generate_embedding_mock)

    door = FakeDoorController()
    result = AccessController(door_controller=door).attempt_access()

    assert result.access_status == AccessStatus.DENIED
    assert result.recognition_status == RecognitionStatus.SPOOF_DETECTED
    assert door.opened is False
    generate_embedding_mock.assert_not_called()  # la reconnaissance ne doit pas être tentée


def test_attempt_access_grants_with_live_motion(temp_settings, monkeypatch):
    """Une rafale avec du mouvement doit passer la vivacité et être reconnue normalement."""
    embedding = np.zeros(128)
    user = create_user(full_name="Malik", face_embedding=embedding)

    moving_frames = [
        np.full((10, 10, 3), value, dtype=np.uint8) for value in (0, 255, 0, 255, 0)
    ]

    monkeypatch.setattr(controller_module, "Camera", lambda source=None: _fake_camera(moving_frames))
    monkeypatch.setattr(controller_module, "detect_single_face", lambda frame: FACE)
    monkeypatch.setattr(controller_module, "generate_embedding", lambda frame, loc: embedding.copy())

    door = FakeDoorController()
    result = AccessController(door_controller=door).attempt_access()

    assert result.access_status == AccessStatus.GRANTED
    assert result.recognition_status == RecognitionStatus.AUTHORIZED
    assert result.user.id == user.id
    assert door.opened is True
