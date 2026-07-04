"""Tests de la comparaison d'embeddings faciaux (FaceRecognizer)."""

from __future__ import annotations

import numpy as np

from dogari.storage.models import User
from dogari.vision.recognizer import FaceRecognizer


def _make_user(user_id: int, embedding: np.ndarray) -> User:
    return User(
        id=user_id,
        full_name=f"User {user_id}",
        role_id=None,
        role_name=None,
        status="active",
        face_image_path=None,
        face_embedding=embedding.astype(np.float64).tobytes(),
        created_at=None,
    )


def test_identify_returns_matching_user_within_tolerance():
    reference = np.zeros(128)
    user = _make_user(1, reference)
    recognizer = FaceRecognizer([user], tolerance=0.6)

    result = recognizer.identify(reference + 0.01)

    assert result.matched is True
    assert result.user.id == 1
    assert result.score > 0.85


def test_identify_returns_no_match_beyond_tolerance():
    reference = np.zeros(128)
    user = _make_user(1, reference)
    recognizer = FaceRecognizer([user], tolerance=0.1)

    far_embedding = np.ones(128) * 5
    result = recognizer.identify(far_embedding)

    assert result.matched is False
    assert result.user is None


def test_identify_with_no_known_users():
    recognizer = FaceRecognizer([], tolerance=0.6)

    result = recognizer.identify(np.zeros(128))

    assert result.matched is False
    assert result.distance is None
