"""Tests du calcul des métriques FAR/FRR/accuracy (scripts/evaluate_recognition.py)."""

from __future__ import annotations

import numpy as np

from dogari.storage.models import User, encode_embedding
from evaluate_recognition import UNKNOWN_LABEL, evaluate_probes


def _gallery_user(user_id: int, name: str, embedding: np.ndarray) -> User:
    return User(
        id=user_id,
        full_name=name,
        role_id=None,
        role_name=None,
        status="active",
        face_image_path=None,
        face_embedding=encode_embedding(embedding),
        created_at=None,
    )


def test_evaluate_probes_computes_expected_metrics():
    alice_ref = np.zeros(128)
    bob_ref = np.ones(128) * 3
    gallery = [_gallery_user(1, "alice", alice_ref), _gallery_user(2, "bob", bob_ref)]

    probes = [
        ("alice", alice_ref + 0.01, "alice_probe_ok.jpg"),  # true accept attendu
        ("bob", np.ones(128) * 10, "bob_probe_fail.jpg"),  # false reject attendu (trop loin)
        (UNKNOWN_LABEL, np.ones(128) * 10, "stranger1.jpg"),  # true reject attendu
        (UNKNOWN_LABEL, bob_ref + 0.01, "stranger_lookalike.jpg"),  # false accept attendu
    ]

    summary = evaluate_probes(gallery, probes, tolerance=0.6)

    assert len(summary.true_accepts) == 1
    assert len(summary.false_rejects) == 1
    assert len(summary.true_rejects) == 1
    assert len(summary.false_accepts) == 1
    assert summary.accuracy == 0.5
    assert summary.far == 0.5
    assert summary.frr == 0.5


def test_evaluate_probes_perfect_match():
    reference = np.zeros(128)
    gallery = [_gallery_user(1, "alice", reference)]
    probes = [("alice", reference.copy(), "alice1.jpg"), (UNKNOWN_LABEL, np.ones(128) * 5, "stranger.jpg")]

    summary = evaluate_probes(gallery, probes, tolerance=0.6)

    assert summary.accuracy == 1.0
    assert summary.far == 0.0
    assert summary.frr == 0.0


def test_evaluate_probes_with_no_impostor_attempts_has_zero_far():
    reference = np.zeros(128)
    gallery = [_gallery_user(1, "alice", reference)]
    probes = [("alice", reference.copy(), "alice1.jpg")]

    summary = evaluate_probes(gallery, probes, tolerance=0.6)

    assert summary.impostor_attempts == []
    assert summary.far == 0.0
