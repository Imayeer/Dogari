"""Tests de l'orchestration du contrôle d'accès (AccessController)."""

from __future__ import annotations

import numpy as np

from dogari.access import controller as controller_module
from dogari.access.controller import AccessController
from dogari.access.door import DoorController
from dogari.core.constants import AccessStatus, RecognitionStatus
from dogari.storage.users_repository import create_user


class FakeDoorController(DoorController):
    def __init__(self) -> None:
        self.opened = False

    def open_door(self, hold_seconds: float | None = None) -> None:
        self.opened = True

    def close_door(self) -> None:
        self.opened = False


def _dummy_frame() -> np.ndarray:
    return np.zeros((10, 10, 3), dtype=np.uint8)


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
