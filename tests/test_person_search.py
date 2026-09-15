"""Tests de la recherche continue d'une personne nommée (access/person_search.py)."""

from __future__ import annotations

import time
from dataclasses import replace
from unittest import mock

import numpy as np
import pytest

from dogari.access import camera_watcher as camera_watcher_module
from dogari.access import person_search as person_search_module
from dogari.core.exceptions import UserNotFoundError
from dogari.storage.sightings_repository import get_sightings
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


def test_find_target_user_raises_when_missing(temp_settings):
    with pytest.raises(UserNotFoundError):
        person_search_module.find_target_user("Personne Inconnue")


def test_find_target_user_returns_match(temp_settings):
    embedding = np.zeros(128)
    user = create_user(full_name="Rania", face_embedding=embedding)

    found = person_search_module.find_target_user("Rania")

    assert found.id == user.id


def test_check_frame_for_target_matched_and_unmatched(monkeypatch):
    target_embedding = np.zeros(128)

    monkeypatch.setattr(person_search_module, "detect_single_face", lambda frame: np.array([0, 0, 10, 10]))
    monkeypatch.setattr(person_search_module, "generate_embedding", lambda frame, face: target_embedding.copy())

    distance = person_search_module.check_frame_for_target(np.zeros((5, 5, 3)), target_embedding, tolerance=0.5)
    assert distance is not None

    monkeypatch.setattr(person_search_module, "generate_embedding", lambda frame, face: np.ones(128) * 10)
    distance = person_search_module.check_frame_for_target(np.zeros((5, 5, 3)), target_embedding, tolerance=0.5)
    assert distance is None


def test_check_frame_for_target_returns_none_when_no_face(monkeypatch):
    monkeypatch.setattr(person_search_module, "detect_single_face", lambda frame: None)

    distance = person_search_module.check_frame_for_target(np.zeros((5, 5, 3)), np.zeros(128), tolerance=0.5)

    assert distance is None


def test_start_search_logs_sightings_and_stop_works(temp_settings, monkeypatch):
    embedding = np.zeros(128)
    user = create_user(full_name="Samir", face_embedding=embedding)

    monkeypatch.setattr(camera_watcher_module, "Camera", lambda source=None: _fake_camera())
    monkeypatch.setattr(person_search_module, "detect_single_face", lambda frame: np.array([0, 0, 10, 10]))
    monkeypatch.setattr(person_search_module, "generate_embedding", lambda frame, face: embedding.copy())
    monkeypatch.setattr(
        person_search_module,
        "settings",
        replace(temp_settings, search_poll_interval_seconds=0.01, search_sighting_cooldown_seconds=0.0),
    )

    search = person_search_module.start_search("Samir", camera_source=0)

    _wait_until(lambda: search.sightings_count >= 1)
    person_search_module.stop_search(search.search_id)

    sightings = get_sightings(search.search_id)
    assert len(sightings) >= 1
    assert sightings[0].full_name == "Samir"
    assert sightings[0].user_id == user.id


def test_stop_search_raises_for_unknown_id(temp_settings):
    with pytest.raises(UserNotFoundError):
        person_search_module.stop_search("does-not-exist")
