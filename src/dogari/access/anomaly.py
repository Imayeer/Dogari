"""Détection d'anomalies simples sur l'historique des tentatives d'accès.

Approche par règles (pas d'apprentissage automatique, aucune donnée
d'entraînement disponible) : chaque règle analyse `access_logs` et signale
des motifs jugés suspects ou inhabituels. Pensé pour être exécuté à la
demande (route API, script) plutôt qu'en continu.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from dogari.core.config import settings
from dogari.core.constants import AccessStatus
from dogari.storage.access_logs_repository import get_recent_logs
from dogari.storage.models import AccessLog

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass
class AnomalyEvent:
    """Anomalie détectée dans l'historique des accès."""

    kind: str
    severity: str  # "warning" ou "critical"
    message: str
    log_ids: list[int]


def _parse(created_at: str) -> datetime:
    return datetime.strptime(created_at, DATETIME_FORMAT)


def detect_repeated_denials(
    logs: list[AccessLog],
    window_minutes: int | None = None,
    threshold: int | None = None,
) -> list[AnomalyEvent]:
    """Signale des séries de refus rapprochés (tentative d'intrusion potentielle)."""
    window_minutes = window_minutes if window_minutes is not None else settings.anomaly_denial_window_minutes
    threshold = threshold if threshold is not None else settings.anomaly_denial_threshold
    window = timedelta(minutes=window_minutes)

    denials = sorted(
        (log for log in logs if log.status in (AccessStatus.DENIED.value, AccessStatus.ERROR.value)),
        key=lambda log: log.created_at,
    )

    events: list[AnomalyEvent] = []
    cluster: list[AccessLog] = []
    for log in denials:
        if cluster and _parse(log.created_at) - _parse(cluster[-1].created_at) > window:
            events.extend(_repeated_denials_event(cluster, window_minutes, threshold))
            cluster = []
        cluster.append(log)
    events.extend(_repeated_denials_event(cluster, window_minutes, threshold))
    return events


def _repeated_denials_event(
    cluster: list[AccessLog], window_minutes: int, threshold: int
) -> list[AnomalyEvent]:
    if len(cluster) < threshold:
        return []
    return [
        AnomalyEvent(
            kind="repeated_denials",
            severity="critical",
            message=(
                f"{len(cluster)} refus en moins de {window_minutes} minutes "
                f"(entre {cluster[0].created_at} et {cluster[-1].created_at})."
            ),
            log_ids=[log.id for log in cluster if log.id is not None],
        )
    ]


def detect_off_hours_access(
    logs: list[AccessLog],
    start_hour: int | None = None,
    end_hour: int | None = None,
) -> list[AnomalyEvent]:
    """Signale les accès autorisés en dehors de la plage horaire habituelle."""
    start_hour = start_hour if start_hour is not None else settings.anomaly_off_hours_start
    end_hour = end_hour if end_hour is not None else settings.anomaly_off_hours_end

    events = []
    for log in logs:
        if log.status != AccessStatus.GRANTED.value:
            continue
        hour = _parse(log.created_at).hour
        if not (start_hour <= hour < end_hour):
            events.append(
                AnomalyEvent(
                    kind="off_hours_access",
                    severity="warning",
                    message=(
                        f"Accès autorisé hors plage horaire habituelle ({log.created_at}, "
                        f"utilisateur : {log.full_name or 'inconnu'})."
                    ),
                    log_ids=[log.id] if log.id is not None else [],
                )
            )
    return events


def detect_high_frequency_attempts(
    logs: list[AccessLog], window_minutes: int = 5, threshold: int = 10
) -> list[AnomalyEvent]:
    """Signale un nombre inhabituel de tentatives (tous statuts) sur une courte période."""
    window = timedelta(minutes=window_minutes)
    ordered = sorted(logs, key=lambda log: log.created_at)

    events: list[AnomalyEvent] = []
    cluster: list[AccessLog] = []
    for log in ordered:
        if cluster and _parse(log.created_at) - _parse(cluster[-1].created_at) > window:
            events.extend(_high_frequency_event(cluster, window_minutes, threshold))
            cluster = []
        cluster.append(log)
    events.extend(_high_frequency_event(cluster, window_minutes, threshold))
    return events


def _high_frequency_event(
    cluster: list[AccessLog], window_minutes: int, threshold: int
) -> list[AnomalyEvent]:
    if len(cluster) < threshold:
        return []
    return [
        AnomalyEvent(
            kind="high_frequency_attempts",
            severity="warning",
            message=(
                f"{len(cluster)} tentatives d'accès en moins de {window_minutes} minutes "
                f"(entre {cluster[0].created_at} et {cluster[-1].created_at})."
            ),
            log_ids=[log.id for log in cluster if log.id is not None],
        )
    ]


def detect_anomalies(logs: list[AccessLog] | None = None) -> list[AnomalyEvent]:
    """Exécute toutes les règles de détection sur l'historique des accès."""
    logs = logs if logs is not None else get_recent_logs(limit=1000)
    events: list[AnomalyEvent] = []
    events.extend(detect_repeated_denials(logs))
    events.extend(detect_off_hours_access(logs))
    events.extend(detect_high_frequency_attempts(logs))
    return events
