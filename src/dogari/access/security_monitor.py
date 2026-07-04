"""Surveillance sécurité continue sur une caméra : détection de foule et d'armes.

Comme pour la recherche de personne, s'appuie sur `CameraWatcher` pour tourner
en tâche de fond et journalise les événements détectés via
`storage/security_events_repository.py`.

La détection de foule (comptage de visages) est une mesure fiable au même
titre que la détection faciale. La détection d'armes, elle, est
EXPÉRIMENTALE (voir `vision/weapon_detector.py`) : désactivée par défaut,
et à ne jamais considérer comme une garantie de sécurité.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

from dogari.access.camera_watcher import CameraWatcher, new_watcher_id
from dogari.core.config import settings
from dogari.core.exceptions import DogariError
from dogari.storage.security_events_repository import create_security_event
from dogari.vision.detector import detect_faces


@dataclass
class SecurityMonitor:
    """État d'une surveillance sécurité continue sur une caméra."""

    monitor_id: str
    camera_source: int | str
    watcher: CameraWatcher
    started_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    @property
    def is_running(self) -> bool:
        return self.watcher.is_running

    @property
    def last_error(self) -> str | None:
        return self.watcher.last_error


_active_monitors: dict[str, SecurityMonitor] = {}
_registry_lock = threading.Lock()


def check_crowd_size(frame: np.ndarray, threshold: int) -> int | None:
    """Retourne le nombre de visages détectés si celui-ci atteint le seuil, sinon None."""
    face_count = len(detect_faces(frame))
    return face_count if face_count >= threshold else None


def _on_frame(camera_source: int | str, frame: np.ndarray) -> None:
    face_count = check_crowd_size(frame, settings.crowd_size_threshold)
    if face_count is not None:
        create_security_event(
            kind="crowd_detected",
            severity="warning",
            message=(
                f"{face_count} personnes détectées simultanément "
                f"(seuil : {settings.crowd_size_threshold})."
            ),
            camera_source=str(camera_source),
        )

    if settings.weapon_detection_enabled:
        from dogari.vision.weapon_detector import detect_weapons  # import différé : dépendance optionnelle lourde

        for detection in detect_weapons(frame):
            create_security_event(
                kind="weapon_detected",
                severity="critical",
                message=(
                    f"Objet potentiellement dangereux détecté : {detection.label} "
                    f"(confiance : {detection.confidence:.2f}). Détection EXPÉRIMENTALE, à vérifier "
                    "manuellement avant toute action."
                ),
                camera_source=str(camera_source),
            )


def start_monitoring(camera_source: int | str) -> SecurityMonitor:
    """Démarre une surveillance sécurité continue (foule, armes) sur une caméra."""
    monitor_id = new_watcher_id()
    watcher = CameraWatcher(
        watcher_id=monitor_id,
        camera_source=camera_source,
        on_frame=lambda frame: _on_frame(camera_source, frame),
        poll_interval_seconds=settings.monitoring_poll_interval_seconds,
    )
    monitor = SecurityMonitor(monitor_id=monitor_id, camera_source=camera_source, watcher=watcher)
    with _registry_lock:
        _active_monitors[monitor_id] = monitor
    watcher.start()
    return monitor


def stop_monitoring(monitor_id: str) -> None:
    """Arrête une surveillance sécurité en cours."""
    with _registry_lock:
        monitor = _active_monitors.get(monitor_id)
    if monitor is None:
        raise DogariError(f"Aucune surveillance active avec l'identifiant {monitor_id!r}.")
    monitor.watcher.stop()


def list_active_monitors() -> list[SecurityMonitor]:
    """Retourne les surveillances actuellement en cours d'exécution."""
    with _registry_lock:
        return [monitor for monitor in _active_monitors.values() if monitor.is_running]
