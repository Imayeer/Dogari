"""Tests du détecteur d'armes expérimental (vision/weapon_detector.py), sans dépendance ultralytics.

Ces tests couvrent uniquement les erreurs attendues (modèle manquant,
dépendance optionnelle absente) : l'inférence réelle nécessite `ultralytics`
et un modèle entraîné, non disponibles dans l'environnement de test.
"""

from __future__ import annotations

import sys
from dataclasses import replace

import pytest

from dogari.core.exceptions import ModelLoadError
from dogari.vision import weapon_detector as weapon_detector_module


def test_detect_weapons_raises_when_model_file_missing(temp_settings, monkeypatch):
    monkeypatch.setattr(weapon_detector_module, "_model", None)
    monkeypatch.setattr(
        weapon_detector_module,
        "settings",
        replace(temp_settings, weapon_model_path=temp_settings.data_dir / "missing_model.pt"),
    )

    with pytest.raises(ModelLoadError, match="introuvable"):
        weapon_detector_module.detect_weapons(object())


def test_detect_weapons_raises_when_ultralytics_not_installed(temp_settings, monkeypatch, tmp_path):
    model_path = tmp_path / "weapon_model.pt"
    model_path.write_bytes(b"fake-weights")

    monkeypatch.setattr(weapon_detector_module, "_model", None)
    monkeypatch.setattr(weapon_detector_module, "settings", replace(temp_settings, weapon_model_path=model_path))
    monkeypatch.setitem(sys.modules, "ultralytics", None)

    with pytest.raises(ModelLoadError, match="ultralytics"):
        weapon_detector_module.detect_weapons(object())
