"""Comparaison d'un visage capturé avec les utilisateurs autorisés enregistrés."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from dogari.core.config import settings
from dogari.storage.models import User
from dogari.vision.embeddings import euclidean_distance, similarity_score


@dataclass
class MatchResult:
    """Résultat de la comparaison d'un embedding avec les utilisateurs connus."""

    user: User | None
    distance: float | None

    @property
    def matched(self) -> bool:
        return self.user is not None

    @property
    def score(self) -> float | None:
        return similarity_score(self.distance) if self.distance is not None else None


class FaceRecognizer:
    """Compare l'embedding d'un visage capturé aux embeddings des utilisateurs actifs."""

    def __init__(self, known_users: list[User], tolerance: float | None = None) -> None:
        self.known_users = [user for user in known_users if user.embedding is not None]
        self.tolerance = tolerance if tolerance is not None else settings.recognition_tolerance

    def identify(self, embedding: np.ndarray) -> MatchResult:
        """Retourne l'utilisateur le plus proche si sa distance est sous le seuil de tolérance."""
        if not self.known_users:
            return MatchResult(user=None, distance=None)

        distances = [
            (user, euclidean_distance(embedding, user.embedding)) for user in self.known_users
        ]
        best_user, best_distance = min(distances, key=lambda pair: pair[1])

        if best_distance <= self.tolerance:
            return MatchResult(user=best_user, distance=best_distance)
        return MatchResult(user=None, distance=best_distance)
