"""Tests de la détection de visages (vision/detector.py).

Couvre en particulier le redimensionnement préalable des images haute
résolution et la rescale des coordonnées retournées vers l'image d'origine
(comportement ajouté après qu'un vrai selfie de téléphone en 1408x1470 ait
échoué à la détection : score de confiance YuNet 0,889 à pleine résolution
contre 0,933 après réduction à ~640px, sous le seuil par défaut de 0,90).
"""

from __future__ import annotations

import sys
from dataclasses import replace
from unittest import mock

import numpy as np
import pytest

from dogari.vision import detector as detector_module

# Détection factice : bbox (x, y, w, h) + 5 points de repère (x, y) + score.
_FAKE_DETECTION = np.array(
    [[10.0, 20.0, 30.0, 40.0, 15, 25, 35, 25, 25, 35, 15, 45, 35, 45, 0.95]], dtype=np.float32
)


class _FakeYuNetDetector:
    def __init__(self):
        self.detect_calls: list[tuple[int, int]] = []

    def setInputSize(self, size):
        pass

    def detect(self, frame):
        self.detect_calls.append(frame.shape[:2])
        return 1, _FAKE_DETECTION.copy()


@pytest.fixture
def fake_cv2(monkeypatch, tmp_path):
    fake_model_path = tmp_path / "fake_yunet.onnx"
    fake_model_path.write_bytes(b"fake")
    monkeypatch.setattr(
        detector_module,
        "settings",
        replace(detector_module.settings, yunet_model_path=fake_model_path, max_detection_dimension=640),
    )
    monkeypatch.setattr(detector_module, "_detector", None)
    monkeypatch.setattr(detector_module, "_detector_input_size", None)

    fake_detector = _FakeYuNetDetector()

    class _FakeFaceDetectorYN:
        @staticmethod
        def create(*args, **kwargs):
            return fake_detector

    fake_cv2_module = mock.MagicMock()
    fake_cv2_module.FaceDetectorYN = _FakeFaceDetectorYN
    fake_cv2_module.resize = mock.Mock(
        side_effect=lambda frame, size: np.zeros((size[1], size[0], 3), dtype=np.uint8)
    )
    monkeypatch.setitem(sys.modules, "cv2", fake_cv2_module)
    return fake_detector, fake_cv2_module


def test_detect_faces_does_not_resize_small_image(fake_cv2):
    fake_detector, fake_cv2_module = fake_cv2
    frame = np.zeros((300, 300, 3), dtype=np.uint8)

    faces = detector_module.detect_faces(frame)

    fake_cv2_module.resize.assert_not_called()
    assert fake_detector.detect_calls == [(300, 300)]
    assert faces[0] == pytest.approx(_FAKE_DETECTION[0])


def test_detect_faces_resizes_large_image_and_rescales_coordinates(fake_cv2):
    fake_detector, fake_cv2_module = fake_cv2
    width, height = 1408, 1470  # dimensions réelles d'un selfie de téléphone ayant échoué en test
    frame = np.zeros((height, width, 3), dtype=np.uint8)

    faces = detector_module.detect_faces(frame)

    fake_cv2_module.resize.assert_called_once()
    resized_shape = fake_detector.detect_calls[0]
    assert max(resized_shape) == 640  # le plus grand côté est ramené à max_detection_dimension
    assert resized_shape[0] < height and resized_shape[1] < width  # image réduite, pas agrandie

    scale = 640 / max(width, height)
    expected = _FAKE_DETECTION[0].copy()
    expected[0:14:2] /= scale
    expected[1:14:2] /= scale

    assert faces[0] == pytest.approx(expected, rel=1e-3)
    assert faces[0][14] == pytest.approx(0.95)  # le score de confiance n'est pas rescalé


def test_detect_faces_returns_empty_list_when_no_detection(fake_cv2):
    fake_detector, _ = fake_cv2
    fake_detector.detect = lambda frame: (0, None)

    faces = detector_module.detect_faces(np.zeros((100, 100, 3), dtype=np.uint8))

    assert faces == []
