"""Configuration centrale du projet Dogari.

Toutes les valeurs peuvent être surchargées via des variables d'environnement
préfixées par ``DOGARI_`` afin de garder le système configurable sans
modifier le code (PC de développement vs Raspberry Pi 5).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# Racine du dépôt (dogari/), calculée depuis src/dogari/core/config.py
BASE_DIR = Path(__file__).resolve().parents[3]


def _env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).expanduser().resolve() if value else default


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    try:
        return float(value) if value is not None else default
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Paramètres de configuration du système Dogari."""

    base_dir: Path = BASE_DIR
    data_dir: Path = field(default_factory=lambda: _env_path("DOGARI_DATA_DIR", BASE_DIR / "data"))

    # Sous-dossiers de données
    database_dir: Path = field(init=False)
    faces_dir: Path = field(init=False)
    logs_dir: Path = field(init=False)
    database_path: Path = field(init=False)

    # Caméra
    camera_source: int | str = field(default_factory=lambda: _env_int("DOGARI_CAMERA_INDEX", 0))

    # Reconnaissance faciale (OpenCV YuNet + SFace, voir vision/detector.py et vision/embeddings.py)
    yunet_model_path: Path = field(
        default_factory=lambda: _env_path(
            "DOGARI_YUNET_MODEL_PATH", BASE_DIR / "models" / "face_detection_yunet_2023mar.onnx"
        )
    )
    sface_model_path: Path = field(
        default_factory=lambda: _env_path(
            "DOGARI_SFACE_MODEL_PATH", BASE_DIR / "models" / "face_recognition_sface_2021dec.onnx"
        )
    )
    # Seuil de distance L2 recommandé par OpenCV Zoo pour les embeddings SFace (128-D, normalisés)
    recognition_tolerance: float = field(
        default_factory=lambda: _env_float("DOGARI_RECOGNITION_TOLERANCE", 1.128)
    )

    # Contrôle de porte
    door_hold_seconds: float = field(default_factory=lambda: _env_float("DOGARI_DOOR_HOLD_SECONDS", 5.0))
    use_gpio: bool = field(default_factory=lambda: _env_bool("DOGARI_USE_GPIO", False))
    gpio_relay_pin: int = field(default_factory=lambda: _env_int("DOGARI_GPIO_RELAY_PIN", 17))

    # Interface web
    web_host: str = field(default_factory=lambda: os.environ.get("DOGARI_WEB_HOST", "0.0.0.0"))
    web_port: int = field(default_factory=lambda: _env_int("DOGARI_WEB_PORT", 8000))

    def __post_init__(self) -> None:
        object.__setattr__(self, "database_dir", self.data_dir / "database")
        object.__setattr__(self, "faces_dir", self.data_dir / "faces")
        object.__setattr__(self, "logs_dir", self.data_dir / "logs")
        object.__setattr__(self, "database_path", self.database_dir / "dogari.db")

    def ensure_directories(self) -> None:
        """Crée les répertoires de données nécessaires s'ils n'existent pas."""
        for directory in (self.database_dir, self.faces_dir, self.logs_dir):
            directory.mkdir(parents=True, exist_ok=True)


settings = Settings()
