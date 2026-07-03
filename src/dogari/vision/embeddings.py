"""Extraction et comparaison des représentations numériques (embeddings) de visages."""

from __future__ import annotations

import numpy as np

from dogari.vision.detector import FaceLocation


def generate_embedding(frame: np.ndarray, face_location: FaceLocation) -> np.ndarray:
    """Génère l'embedding (vecteur 128-D) d'un visage détecté dans une image."""
    import face_recognition  # import différé : dépendance lourde optionnelle

    rgb_frame = frame[:, :, ::-1] if frame.shape[-1] == 3 else frame
    encodings = face_recognition.face_encodings(rgb_frame, known_face_locations=[face_location])
    if not encodings:
        raise ValueError("Impossible de générer un embedding pour le visage fourni.")
    return encodings[0]


def euclidean_distance(embedding_a: np.ndarray, embedding_b: np.ndarray) -> float:
    """Distance euclidienne entre deux embeddings faciaux (plus petit = plus similaire)."""
    return float(np.linalg.norm(embedding_a - embedding_b))


def similarity_score(distance: float) -> float:
    """Convertit une distance euclidienne en score de similarité borné entre 0 et 1."""
    return max(0.0, 1.0 - distance)
