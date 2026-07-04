"""Détection de vivacité (anti-usurpation) par analyse de mouvement inter-images.

Approche volontairement simple pour un MVP : une photo ou un écran statique
présenté à la caméra produit un visage quasiment identique d'une image à
l'autre, alors qu'un visage réel présente toujours un léger mouvement
(respiration, micro-mouvements, clignements) même sur une rafale de
quelques centaines de millisecondes.

Limite connue : le bruit du capteur seul peut produire un écart non nul
même sur une scène parfaitement statique, et cette méthode ne protège pas
contre une attaque par rejeu vidéo. `DOGARI_LIVENESS_MOTION_THRESHOLD` doit
être calibré avec `scripts/evaluate_recognition.py`-like des essais réels ;
une évolution vers un modèle anti-usurpation dédié (ex. MiniFASNet) est
envisageable si une sécurité plus forte est nécessaire.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from dogari.core.config import settings
from dogari.vision.detector import FaceDetection

_CROP_SIZE = (64, 64)


@dataclass
class LivenessResult:
    """Résultat de l'analyse de vivacité sur une rafale d'images."""

    is_live: bool
    motion_score: float


def _crop_face_gray(frame: np.ndarray, face: FaceDetection) -> np.ndarray:
    """Recadre la région du visage et la convertit en niveaux de gris, taille fixe."""
    import cv2  # import différé : dépendance lourde optionnelle

    height, width = frame.shape[:2]
    x, y, w, h = face[:4].astype(int)
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(width, x + w), min(height, y + h)
    crop = frame[y1:y2, x1:x2]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    return cv2.resize(gray, _CROP_SIZE).astype(np.float32)


def check_liveness(frames: list[np.ndarray], face: FaceDetection) -> LivenessResult:
    """Analyse une rafale d'images et tente de détecter une usurpation par photo/écran statique.

    Avec une seule image, le mouvement ne peut pas être évalué : le contrôle
    est alors considéré comme réussi par défaut (cas d'une image unique fournie
    directement, par exemple à l'enregistrement d'un utilisateur).
    """
    if len(frames) < 2:
        return LivenessResult(is_live=True, motion_score=float("inf"))

    crops = [_crop_face_gray(frame, face) for frame in frames]
    diffs = [float(np.mean(np.abs(crops[i] - crops[i - 1]))) for i in range(1, len(crops))]
    motion_score = sum(diffs) / len(diffs)
    return LivenessResult(is_live=motion_score >= settings.liveness_motion_threshold, motion_score=motion_score)
