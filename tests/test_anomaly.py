"""Tests de la détection d'anomalies sur l'historique des accès (access/anomaly.py)."""

from __future__ import annotations

from dogari.access.anomaly import (
    detect_anomalies,
    detect_high_frequency_attempts,
    detect_off_hours_access,
    detect_repeated_denials,
)
from dogari.core.constants import AccessStatus
from dogari.storage.models import AccessLog


def _log(log_id: int, status: str, created_at: str, full_name: str | None = None) -> AccessLog:
    return AccessLog(
        id=log_id,
        user_id=None,
        full_name=full_name,
        status=status,
        similarity_score=None,
        camera_source="0",
        message="",
        created_at=created_at,
    )


def test_detect_repeated_denials_flags_close_cluster():
    logs = [
        _log(1, AccessStatus.DENIED.value, "2026-01-01 10:00:00"),
        _log(2, AccessStatus.DENIED.value, "2026-01-01 10:01:00"),
        _log(3, AccessStatus.DENIED.value, "2026-01-01 10:02:00"),
        _log(4, AccessStatus.DENIED.value, "2026-01-01 10:03:00"),
        _log(5, AccessStatus.DENIED.value, "2026-01-01 10:04:00"),
    ]

    events = detect_repeated_denials(logs, window_minutes=10, threshold=5)

    assert len(events) == 1
    assert events[0].kind == "repeated_denials"
    assert events[0].severity == "critical"
    assert set(events[0].log_ids) == {1, 2, 3, 4, 5}


def test_detect_repeated_denials_ignores_sparse_denials():
    logs = [
        _log(1, AccessStatus.DENIED.value, "2026-01-01 08:00:00"),
        _log(2, AccessStatus.DENIED.value, "2026-01-01 09:00:00"),
        _log(3, AccessStatus.DENIED.value, "2026-01-01 10:00:00"),
    ]

    events = detect_repeated_denials(logs, window_minutes=10, threshold=5)

    assert events == []


def test_detect_off_hours_access_flags_granted_outside_window():
    logs = [
        _log(1, AccessStatus.GRANTED.value, "2026-01-01 02:30:00", full_name="Nadia"),
        _log(2, AccessStatus.GRANTED.value, "2026-01-01 10:00:00", full_name="Omar"),
    ]

    events = detect_off_hours_access(logs, start_hour=7, end_hour=20)

    assert len(events) == 1
    assert events[0].kind == "off_hours_access"
    assert events[0].log_ids == [1]


def test_detect_high_frequency_attempts_flags_burst():
    logs = [_log(i, AccessStatus.DENIED.value, f"2026-01-01 10:00:{i:02d}") for i in range(10)]

    events = detect_high_frequency_attempts(logs, window_minutes=5, threshold=10)

    assert len(events) == 1
    assert events[0].kind == "high_frequency_attempts"


def test_detect_anomalies_aggregates_all_rules(temp_settings):
    logs = [
        _log(1, AccessStatus.GRANTED.value, "2026-01-01 03:00:00", full_name="Paul"),
    ]

    events = detect_anomalies(logs)

    assert any(event.kind == "off_hours_access" for event in events)
