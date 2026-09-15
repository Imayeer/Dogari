"""Abstraction de la caméra (webcam USB ou caméra Raspberry Pi via OpenCV)."""

from __future__ import annotations

import time
from types import TracebackType
from typing import Optional

import numpy as np

from dogari.core.config import settings
from dogari.core.exceptions import CameraError


class Camera:
    """Enveloppe cv2.VideoCapture avec gestion d'erreurs et context manager.

    L'import d'OpenCV est différé jusqu'à l'instanciation afin que le reste
    de l'application reste utilisable (tests, API) sur une machine où la
    dépendance n'est pas encore installée.
    """

    def __init__(self, source: int | str | None = None) -> None:
        self.source = source if source is not None else settings.camera_source
        self._capture = None

    def open(self) -> "Camera":
        import cv2  # import différé : dépendance lourde optionnelle

        self._capture = cv2.VideoCapture(self.source)
        if not self._capture.isOpened():
            self._capture.release()
            self._capture = None
            raise CameraError(f"Impossible d'ouvrir la source caméra: {self.source!r}")
        return self

    def capture_frame(self) -> np.ndarray:
        """Capture une image unique depuis la caméra (format BGR OpenCV)."""
        if self._capture is None:
            raise CameraError("La caméra n'est pas ouverte. Utilisez `with Camera() as cam:`.")
        success, frame = self._capture.read()
        if not success or frame is None:
            raise CameraError("Échec de la capture d'image depuis la caméra.")
        return frame

    def capture_burst(self, count: int, interval: float) -> list[np.ndarray]:
        """Capture plusieurs images successives, espacées de `interval` secondes.

        Utilisé pour la détection de vivacité (voir `vision/liveness.py`), qui a
        besoin de plusieurs images rapprochées pour évaluer le mouvement.
        """
        frames = [self.capture_frame()]
        for _ in range(count - 1):
            time.sleep(interval)
            frames.append(self.capture_frame())
        return frames

    def release(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def __enter__(self) -> "Camera":
        return self.open()

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.release()


def save_frame(frame: np.ndarray, path: str) -> None:
    """Sauvegarde une image (frame OpenCV) sur le disque."""
    import cv2

    success = cv2.imwrite(path, frame)
    if not success:
        raise CameraError(f"Impossible d'enregistrer l'image vers {path!r}")
