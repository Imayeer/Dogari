"""Tests de la génération de rapports de synthèse (access/reports.py)."""

from __future__ import annotations

from datetime import datetime

from dogari.access.reports import generate_report, render_report_csv, render_report_text
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


def test_generate_report_aggregates_counts_and_daily_breakdown():
    logs = [
        _log(1, AccessStatus.GRANTED.value, "2026-01-01 08:00:00", full_name="Alice"),
        _log(2, AccessStatus.DENIED.value, "2026-01-01 09:00:00"),
        _log(3, AccessStatus.GRANTED.value, "2026-01-02 08:00:00", full_name="Bob"),
        _log(4, AccessStatus.ERROR.value, "2026-01-02 10:00:00"),
    ]

    report = generate_report(logs, datetime(2026, 1, 1), datetime(2026, 1, 3))

    assert report.total_attempts == 4
    assert report.granted == 2
    assert report.denied == 1
    assert report.error == 1
    assert report.unique_users == ["Alice", "Bob"]
    assert [day.date for day in report.daily_breakdown] == ["2026-01-01", "2026-01-02"]
    assert report.daily_breakdown[0].total == 2
    assert report.daily_breakdown[1].total == 2


def test_generate_report_with_no_logs():
    report = generate_report([], datetime(2026, 1, 1), datetime(2026, 1, 2))

    assert report.total_attempts == 0
    assert report.daily_breakdown == []
    assert report.unique_users == []


def test_render_report_text_includes_key_figures():
    logs = [_log(1, AccessStatus.GRANTED.value, "2026-01-01 08:00:00", full_name="Alice")]
    report = generate_report(logs, datetime(2026, 1, 1), datetime(2026, 1, 2))

    text = render_report_text(report)

    assert "Tentatives totales : 1" in text
    assert "Alice" in text


def test_render_report_csv_has_header_and_rows():
    logs = [_log(1, AccessStatus.GRANTED.value, "2026-01-01 08:00:00")]
    report = generate_report(logs, datetime(2026, 1, 1), datetime(2026, 1, 2))

    csv_text = render_report_csv(report)

    lines = csv_text.strip().splitlines()
    assert lines[0] == "date,total,granted,denied,error"
    assert lines[1] == "2026-01-01,1,1,0,0"


def test_generate_report_for_last_days_uses_database(temp_settings):
    from dogari.access.reports import generate_report_for_last_days
    from dogari.storage.access_logs_repository import create_log

    create_log(status=AccessStatus.GRANTED.value, full_name="Chris")

    report = generate_report_for_last_days(7)

    assert report.total_attempts == 1
    assert report.granted == 1
