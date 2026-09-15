"""Détection de visages via YuNet (modèle ONNX embarqué dans le module DNN d'OpenCV).

YuNet est préféré à un détecteur basé sur dlib car il ne nécessite aucune
compilation (contrairement à dlib, coûteux à construire sur Raspberry Pi) et
tourne directement via `cv2.dnn`, déjà fourni par `opencv-python`.
"""

from __future__ import annotations

import numpy as np

from dogari.core.config import settings
from dogari.core.exceptions import ModelLoadError

# Une détection YuNet : [x, y, w, h, <5 points de repère (x, y)>, score_confiance] soit 15 valeurs.
FaceDetection = np.ndarray

_detector = None
_detector_input_size: tuple[int, int] | None = None


def _get_detector(input_size: tuple[int, int]):
    """Charge (une seule fois) et retourne le détecteur YuNet, adapté à la taille de l'image."""
    import cv2  # import différé : dépendance lourde optionnelle

    global _detector, _detector_input_size

    if not settings.yunet_model_path.is_file():
        raise ModelLoadError(
            f"Modèle YuNet introuvable : {settings.yunet_model_path}. "
            "Téléchargez-le avec `python scripts/download_models.py` ou consultez le README."
        )

    if _detector is None:
        _detector = cv2.FaceDetectorYN.create(str(settings.yunet_model_path), "", input_size)
        _detector_input_size = input_size
    elif _detector_input_size != input_size:
        _detector.setInputSize(input_size)
        _detector_input_size = input_size

    return _detector


def detect_faces(frame: np.ndarray) -> list[FaceDetection]:
    """Détecte les visages présents dans une image (format BGR OpenCV).

    Les images dont le plus grand côté dépasse `settings.max_detection_dimension`
    sont réduites avant détection (YuNet est moins confiant sur des photos très
    haute résolution, typiquement des selfies de téléphone - voir le commentaire
    dans `core/config.py`) ; les coordonnées retournées sont rescalées vers les
    dimensions de l'image d'origine, pour rester utilisables par les appelants
    (ex. `embeddings.generate_embedding`, qui aligne le visage sur `frame`).
    """
    import cv2  # import différé : dépendance lourde optionnelle

    height, width = frame.shape[:2]

    scale = 1.0
    detection_frame = frame
    largest_side = max(width, height)
    if largest_side > settings.max_detection_dimension:
        scale = settings.max_detection_dimension / largest_side
        detection_frame = cv2.resize(frame, (round(width * scale), round(height * scale)))

    det_height, det_width = detection_frame.shape[:2]
    detector = _get_detector((det_width, det_height))
    _, faces = detector.detect(detection_frame)
    if faces is None:
        return []

    if scale != 1.0:
        faces = faces.copy()
        faces[:, 0:14:2] /= scale  # coordonnées x (bbox + 5 points de repère)
        faces[:, 1:14:2] /= scale  # coordonnées y

    return list(faces)


def detect_single_face(frame: np.ndarray) -> FaceDetection | None:
    """Retourne l'unique visage détecté, ou None si aucun visage n'est présent.

    Si plusieurs visages sont détectés, retourne le plus grand (le plus proche
    de la caméra), ce qui correspond à l'usage type d'un contrôle d'accès.
    """
    faces = detect_faces(frame)
    if not faces:
        return None
    return max(faces, key=lambda face: face[2] * face[3])
