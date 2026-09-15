"""Détection best-effort d'armes (EXPÉRIMENTAL, désactivé par défaut).

ATTENTION — contrairement à la détection/reconnaissance faciale (YuNet/SFace),
il n'existe pas de modèle de référence officiellement maintenu et validé pour
la détection d'armes. Ce module s'appuie sur un modèle YOLO (Ultralytics)
préentraîné par la communauté, dont le taux de faux positifs/négatifs n'est
PAS garanti. Ne doit jamais être la seule mesure de sécurité d'un déploiement
réel : à combiner avec une supervision humaine et d'autres contrôles.

Dépendance optionnelle et lourde (`ultralytics`, qui installe `torch`) : voir
`requirements-weapon-detection.txt`, non incluse dans `requirements.txt` par
défaut. Le modèle lui-même (fichier de poids) doit être fourni séparément
(voir README) : aucun modèle de détection d'armes officiel n'est distribué
par OpenCV Zoo comme c'est le cas pour YuNet/SFace.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from dogari.core.config import settings
from dogari.core.exceptions import ModelLoadError

_model = None


@dataclass
class WeaponDetection:
    """Une détection d'arme potentielle (best-effort, à vérifier manuellement)."""

    label: str
    confidence: float
    box: tuple[int, int, int, int]  # x1, y1, x2, y2


def _get_model():
    """Charge (une seule fois) le modèle YOLO de détection d'armes."""
    global _model
    if _model is not None:
        return _model

    if not settings.weapon_model_path.is_file():
        raise ModelLoadError(
            f"Modèle de détection d'armes introuvable : {settings.weapon_model_path}. "
            "Fonctionnalité EXPÉRIMENTALE : voir le README pour obtenir/entraîner un modèle."
        )
    try:
        from ultralytics import YOLO  # dépendance optionnelle, voir requirements-weapon-detection.txt
    except ImportError as exc:
        raise ModelLoadError(
            "Le paquet 'ultralytics' est requis pour la détection d'armes. Installez-le avec "
            "`pip install -r requirements-weapon-detection.txt`."
        ) from exc

    _model = YOLO(str(settings.weapon_model_path))
    return _model


def detect_weapons(frame: np.ndarray) -> list[WeaponDetection]:
    """Analyse une image et retourne les armes potentielles détectées (best-effort, non garanti)."""
    model = _get_model()
    results = model.predict(frame, conf=settings.weapon_confidence_threshold, verbose=False)

    detections: list[WeaponDetection] = []
    for result in results:
        for box in result.boxes:
            label = result.names[int(box.cls[0])]
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = (int(value) for value in box.xyxy[0])
            detections.append(WeaponDetection(label=label, confidence=confidence, box=(x1, y1, x2, y2)))
    return detections
