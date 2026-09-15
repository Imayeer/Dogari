"""Infrastructure générique de surveillance continue d'une caméra (thread de fond).

Réutilisée par la recherche de personne (`access/person_search.py`) et la
surveillance sécurité (`access/security_monitor.py` : foule, armes). Chaque
`CameraWatcher` ouvre une caméra une seule fois puis appelle `on_frame` sur
chaque image capturée, jusqu'à ce que `stop()` soit appelé.

Limite connue : le registre des watchers actifs (dans `person_search.py` et
`security_monitor.py`) est en mémoire dans le processus web ; il ne survit pas
à un redémarrage et ne fonctionne qu'avec un seul worker uvicorn. Adapté au
MVP, à revoir si un déploiement multi-worker est envisagé.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from dogari.core.exceptions import CameraError
from dogari.vision.camera import Camera


def new_watcher_id() -> str:
    """Génère un identifiant unique pour un watcher (recherche ou surveillance)."""
    return str(uuid.uuid4())


@dataclass
class CameraWatcher:
    """Exécute `on_frame(frame)` en boucle sur une caméra, dans un thread de fond."""

    watcher_id: str
    camera_source: int | str
    on_frame: Callable[[np.ndarray], None]
    poll_interval_seconds: float
    stop_event: threading.Event = field(default_factory=threading.Event)
    thread: threading.Thread | None = None
    last_error: str | None = None

    def _run(self) -> None:
        try:
            with Camera(self.camera_source) as camera:
                while not self.stop_event.is_set():
                    try:
                        frame = camera.capture_frame()
                        self.on_frame(frame)
                    except CameraError as exc:
                        self.last_error = str(exc)
                    self.stop_event.wait(self.poll_interval_seconds)
        except CameraError as exc:
            self.last_error = str(exc)

    def start(self) -> None:
        """Démarre la boucle de capture dans un thread de fond (daemon)."""
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """Signale l'arrêt de la boucle ; ne bloque pas jusqu'à l'arrêt effectif du thread."""
        self.stop_event.set()

    @property
    def is_running(self) -> bool:
        return not self.stop_event.is_set()
