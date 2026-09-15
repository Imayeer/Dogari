"""Fixtures partagées pour les tests Dogari."""

from __future__ import annotations

import pytest

from dogari.core.config import Settings
from dogari.storage import database as database_module
from dogari.storage.database import initialize_database


@pytest.fixture
def temp_settings(tmp_path, monkeypatch):
    """Isole chaque test dans sa propre base de données SQLite temporaire."""
    test_settings = Settings(data_dir=tmp_path / "data")
    test_settings.ensure_directories()
    monkeypatch.setattr(database_module, "settings", test_settings)
    initialize_database()
    return test_settings
