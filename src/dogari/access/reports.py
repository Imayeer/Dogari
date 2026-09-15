"""Génération de rapports périodiques de synthèse sur l'historique des accès.

Pensé pour être lancé à la demande (route API, script planifié via cron) plutôt
que de tourner en tâche de fond : `generate_report_for_last_days` couvre un usage
classique (rapport quotidien/hebdomadaire), et réutilise `access/anomaly.py` pour
inclure les anomalies détectées sur la même période.
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from dogari.access.anomaly import AnomalyEvent, detect_anomalies
from dogari.core.constants import AccessStatus
from dogari.storage.access_logs_repository import get_logs_between
from dogari.storage.models import AccessLog

DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass
class DailyStats:
    """Statistiques d'accès agrégées pour une journée."""

    date: str
    total: int
    granted: int
    denied: int
    error: int


@dataclass
class AccessReport:
    """Rapport de synthèse sur une période donnée."""

    period_start: str
    period_end: str
    total_attempts: int
    granted: int
    denied: int
    error: int
    unique_users: list[str]
    daily_breakdown: list[DailyStats]
    anomalies: list[AnomalyEvent]


def _count_by_status(logs: list[AccessLog], status: str) -> int:
    return sum(1 for log in logs if log.status == status)


def generate_report(logs: list[AccessLog], period_start: datetime, period_end: datetime) -> AccessReport:
    """Agrège une liste de tentatives d'accès en un rapport de synthèse."""
    by_day: dict[str, list[AccessLog]] = defaultdict(list)
    for log in logs:
        day = datetime.strptime(log.created_at, DATETIME_FORMAT).strftime(DATE_FORMAT)
        by_day[day].append(log)

    daily_breakdown = [
        DailyStats(
            date=day,
            total=len(day_logs),
            granted=_count_by_status(day_logs, AccessStatus.GRANTED.value),
            denied=_count_by_status(day_logs, AccessStatus.DENIED.value),
            error=_count_by_status(day_logs, AccessStatus.ERROR.value),
        )
        for day, day_logs in sorted(by_day.items())
    ]

    unique_users = sorted({log.full_name for log in logs if log.full_name})

    return AccessReport(
        period_start=period_start.strftime(DATE_FORMAT),
        period_end=period_end.strftime(DATE_FORMAT),
        total_attempts=len(logs),
        granted=_count_by_status(logs, AccessStatus.GRANTED.value),
        denied=_count_by_status(logs, AccessStatus.DENIED.value),
        error=_count_by_status(logs, AccessStatus.ERROR.value),
        unique_users=unique_users,
        daily_breakdown=daily_breakdown,
        anomalies=detect_anomalies(logs),
    )


def generate_report_for_last_days(days: int) -> AccessReport:
    """Génère un rapport couvrant les `days` derniers jours jusqu'à maintenant."""
    period_end = datetime.now()
    period_start = period_end - timedelta(days=days)
    logs = get_logs_between(period_start.strftime(DATETIME_FORMAT), period_end.strftime(DATETIME_FORMAT))
    return generate_report(logs, period_start, period_end)


def render_report_text(report: AccessReport) -> str:
    """Formate un rapport en texte brut (console, pièce jointe, annexe de rapport)."""
    lines = [
        "=== Rapport d'accès Dogari ===",
        f"Période : {report.period_start} au {report.period_end}",
        "",
        f"Tentatives totales : {report.total_attempts}",
        f"  Autorisées : {report.granted}",
        f"  Refusées   : {report.denied}",
        f"  Erreurs    : {report.error}",
        "",
        f"Utilisateurs distincts vus : {len(report.unique_users)}"
        + (f" ({', '.join(report.unique_users)})" if report.unique_users else ""),
        "",
        "Répartition par jour :",
    ]
    if report.daily_breakdown:
        for day in report.daily_breakdown:
            lines.append(
                f"  {day.date} : {day.total} tentative(s) "
                f"({day.granted} autorisée(s), {day.denied} refusée(s), {day.error} erreur(s))"
            )
    else:
        lines.append("  (aucune tentative sur la période)")

    lines.append("")
    lines.append(f"Anomalies détectées : {len(report.anomalies)}")
    for anomaly in report.anomalies:
        lines.append(f"  [{anomaly.severity.upper()}] {anomaly.message}")

    return "\n".join(lines)


def render_report_csv(report: AccessReport) -> str:
    """Formate la répartition quotidienne du rapport en CSV (ouvrable dans un tableur)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["date", "total", "granted", "denied", "error"])
    for day in report.daily_breakdown:
        writer.writerow([day.date, day.total, day.granted, day.denied, day.error])
    return buffer.getvalue()
