"""Détection de visages dans une image."""

from __future__ import annotations

import numpy as np

# Emplacement d'un visage : (top, right, bottom, left), tel que retourné par face_recognition
FaceLocation = tuple[int, int, int, int]


def detect_faces(frame: np.ndarray) -> list[FaceLocation]:
    """Détecte les visages présents dans une image (format RGB ou BGR OpenCV).

    Utilise la bibliothèque `face_recognition` (basée sur dlib/HOG), la
    dépendance la plus légère recommandée par le projet pour un usage
    embarqué sur Raspberry Pi.
    """
    import face_recognition  # import différé : dépendance lourde optionnelle

    rgb_frame = frame[:, :, ::-1] if frame.shape[-1] == 3 else frame
    return face_recognition.face_locations(rgb_frame)


def detect_single_face(frame: np.ndarray) -> FaceLocation | None:
    """Retourne l'unique visage détecté, ou None si aucun visage n'est présent.

    Si plusieurs visages sont détectés, retourne le plus grand (le plus proche
    de la caméra), ce qui correspond à l'usage type d'un contrôle d'accès.
    """
    locations = detect_faces(frame)
    if not locations:
        return None
    return max(locations, key=lambda loc: (loc[2] - loc[0]) * (loc[1] - loc[3]))
