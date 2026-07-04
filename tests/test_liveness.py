"""Tests de la détection de vivacité (vision/liveness.py)."""

from __future__ import annotations

import numpy as np

from dogari.vision.liveness import check_liveness

FACE = np.array([0, 0, 20, 20])  # x, y, w, h : couvre toute l'image de test


def _solid_frame(value: int) -> np.ndarray:
    return np.full((20, 20, 3), value, dtype=np.uint8)


def test_single_frame_is_always_considered_live():
    result = check_liveness([_solid_frame(128)], FACE)

    assert result.is_live is True


def test_identical_frames_are_flagged_as_spoof():
    frames = [_solid_frame(128) for _ in range(5)]

    result = check_liveness(frames, FACE)

    assert result.motion_score == 0.0
    assert result.is_live is False


def test_frames_with_strong_variation_are_flagged_as_live():
    frames = [_solid_frame(0), _solid_frame(255), _solid_frame(0), _solid_frame(255)]

    result = check_liveness(frames, FACE)

    assert result.motion_score > 100
    assert result.is_live is True
