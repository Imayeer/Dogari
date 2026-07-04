"""Tests de la surveillance sécurité continue (access/security_monitor.py)."""

from __future__ import annotations

import time
from dataclasses import replace
from unittest import mock

import numpy as np
import pytest

from dogari.access import camera_watcher as camera_watcher_module
from dogari.access import security_monitor as security_monitor_module
from dogari.core.exceptions import DogariError
from dogari.storage.security_events_repository import get_recent_security_events


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


def test_check_crowd_size_flags_when_threshold_reached(monkeypatch):
    monkeypatch.setattr(security_monitor_module, "detect_faces", lambda frame: [object()] * 6)

    result = security_monitor_module.check_crowd_size(np.zeros((5, 5, 3)), threshold=5)

    assert result == 6


def test_check_crowd_size_returns_none_below_threshold(monkeypatch):
    monkeypatch.setattr(security_monitor_module, "detect_faces", lambda frame: [object()] * 2)

    result = security_monitor_module.check_crowd_size(np.zeros((5, 5, 3)), threshold=5)

    assert result is None


def test_start_monitoring_logs_crowd_event_and_stop_works(temp_settings, monkeypatch):
    monkeypatch.setattr(camera_watcher_module, "Camera", lambda source=None: _fake_camera())
    monkeypatch.setattr(security_monitor_module, "detect_faces", lambda frame: [object()] * 7)
    monkeypatch.setattr(
        security_monitor_module,
        "settings",
        replace(temp_settings, monitoring_poll_interval_seconds=0.01, crowd_size_threshold=5),
    )

    monitor = security_monitor_module.start_monitoring(camera_source=0)

    _wait_until(lambda: len(get_recent_security_events()) >= 1)
    security_monitor_module.stop_monitoring(monitor.monitor_id)

    events = get_recent_security_events()
    assert events[0].kind == "crowd_detected"
    assert events[0].severity == "warning"


def test_stop_monitoring_raises_for_unknown_id(temp_settings):
    with pytest.raises(DogariError):
        security_monitor_module.stop_monitoring("does-not-exist")
