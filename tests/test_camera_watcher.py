"""Tests de l'infrastructure générique de surveillance caméra (access/camera_watcher.py)."""

from __future__ import annotations

import time
from unittest import mock

import numpy as np
import pytest

from dogari.access import camera_watcher as camera_watcher_module
from dogari.access.camera_watcher import CameraWatcher, new_watcher_id


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


def test_watcher_calls_on_frame_repeatedly_until_stopped(monkeypatch):
    monkeypatch.setattr(camera_watcher_module, "Camera", lambda source=None: _fake_camera())

    calls = []
    watcher = CameraWatcher(
        watcher_id=new_watcher_id(),
        camera_source=0,
        on_frame=lambda frame: calls.append(frame),
        poll_interval_seconds=0.01,
    )

    watcher.start()
    _wait_until(lambda: len(calls) >= 3)
    watcher.stop()

    count_after_stop = len(calls)
    time.sleep(0.1)  # laisse le temps au thread de vraiment s'arrêter
    assert len(calls) in (count_after_stop, count_after_stop + 1)  # au plus un appel en cours au moment du stop
    assert watcher.is_running is False


def test_watcher_records_camera_error(monkeypatch):
    from dogari.core.exceptions import CameraError

    def _raise_camera_error(source=None):
        raise CameraError("caméra indisponible")

    monkeypatch.setattr(camera_watcher_module, "Camera", _raise_camera_error)

    watcher = CameraWatcher(
        watcher_id=new_watcher_id(), camera_source=0, on_frame=lambda frame: None, poll_interval_seconds=0.01
    )
    watcher.start()
    _wait_until(lambda: watcher.last_error is not None)

    assert "caméra indisponible" in watcher.last_error
    watcher.stop()
