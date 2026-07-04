"""Extraction et comparaison des embeddings de visages via SFace (modèle ONNX, module DNN d'OpenCV).

SFace est préféré à un modèle basé sur dlib pour les mêmes raisons que YuNet
(voir `detector.py`) : aucune compilation requise, tourne via `cv2.dnn`. Ses
embeddings 128-D sont normalisés par le réseau ; le seuil de distance L2
recommandé par OpenCV Zoo est 1.128 (voir `core/config.py`).
"""

from __future__ import annotations

import numpy as np

from dogari.core.config import settings
from dogari.core.exceptions import ModelLoadError
from dogari.vision.detector import FaceDetection

_recognizer = None


def _get_recognizer():
    """Charge (une seule fois) et retourne le modèle de reconnaissance SFace."""
    import cv2  # import différé : dépendance lourde optionnelle

    global _recognizer

    if not settings.sface_model_path.is_file():
        raise ModelLoadError(
            f"Modèle SFace introuvable : {settings.sface_model_path}. "
            "Téléchargez-le avec `python scripts/download_models.py` ou consultez le README."
        )

    if _recognizer is None:
        _recognizer = cv2.FaceRecognizerSF.create(str(settings.sface_model_path), "")

    return _recognizer


def generate_embedding(frame: np.ndarray, face: FaceDetection) -> np.ndarray:
    """Génère l'embedding (vecteur 128-D) d'un visage détecté dans une image."""
    recognizer = _get_recognizer()
    aligned_face = recognizer.alignCrop(frame, face)
    feature = recognizer.feature(aligned_face)
    return feature.flatten()


def euclidean_distance(embedding_a: np.ndarray, embedding_b: np.ndarray) -> float:
    """Distance euclidienne (L2) entre deux embeddings faciaux (plus petit = plus similaire)."""
    return float(np.linalg.norm(embedding_a - embedding_b))


def similarity_score(distance: float) -> float:
    """Convertit une distance L2 en score de similarité borné entre 0 et 1.

    Les embeddings SFace sont normalisés : la distance maximale entre deux
    vecteurs unitaires est 2.0, utilisée ici pour l'échelle du score.
    """
    return max(0.0, 1.0 - distance / 2.0)
