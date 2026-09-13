"""Tests du calcul des métriques FAR/FRR/accuracy (scripts/evaluate_recognition.py)."""

from __future__ import annotations

import sys
from unittest import mock

import numpy as np

import dogari.vision.detector as detector_module
import dogari.vision.embeddings as embeddings_module
from dogari.storage.models import User, encode_embedding
from evaluate_recognition import UNKNOWN_LABEL, evaluate_probes, load_gallery, load_probes, sweep_tolerances


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


def test_sweep_tolerances_brackets_the_configured_default():
    """Une plage figée (ex. 0.30-0.70) devient fausse dès que le défaut change (régression réelle :
    DOGARI_RECOGNITION_TOLERANCE=1.128 n'était atteint par aucune valeur de l'ancienne plage)."""
    values = sweep_tolerances(1.128)

    assert min(values) < 1.128 < max(values)


def test_sweep_tolerances_never_goes_below_a_sane_floor():
    values = sweep_tolerances(center=0.1, span=0.4)

    assert min(values) >= 0.05


def _fake_vision(monkeypatch):
    fake_cv2 = mock.MagicMock()
    fake_cv2.imread = mock.Mock(return_value=np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2)
    monkeypatch.setattr(detector_module, "detect_single_face", lambda frame: np.array([0, 0, 10, 10]))
    monkeypatch.setattr(embeddings_module, "generate_embedding", lambda frame, face: np.zeros(128))


def test_load_probes_normalizes_french_unknown_alias(tmp_path, monkeypatch):
    """Régression réelle : un dossier probes/inconnu/ était traité comme une vraie identité
    'inconnu' plutôt que reconnu comme les imposteurs attendus par probes/unknown/, faisant
    compter un rejet correct comme un échec (FRR gonflé à tort)."""
    _fake_vision(monkeypatch)
    probes_dir = tmp_path / "probes"
    (probes_dir / "alice").mkdir(parents=True)
    (probes_dir / "alice" / "photo.jpg").write_bytes(b"fake")
    (probes_dir / "inconnu").mkdir()
    (probes_dir / "inconnu" / "photo.jpg").write_bytes(b"fake")

    probes = load_probes(probes_dir)

    labels = {label for label, _, _ in probes}
    assert labels == {"alice", UNKNOWN_LABEL}


def test_load_gallery_skips_unknown_alias_folder(tmp_path, monkeypatch, capsys):
    _fake_vision(monkeypatch)
    gallery_dir = tmp_path / "gallery"
    (gallery_dir / "alice").mkdir(parents=True)
    (gallery_dir / "alice" / "photo.jpg").write_bytes(b"fake")
    (gallery_dir / "inconnu").mkdir()
    (gallery_dir / "inconnu" / "photo.jpg").write_bytes(b"fake")

    gallery = load_gallery(gallery_dir)

    assert [u.full_name for u in gallery] == ["alice"]
    captured = capsys.readouterr()
    assert "inconnu" in captured.out
