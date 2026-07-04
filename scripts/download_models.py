"""Télécharge les modèles ONNX YuNet (détection) et SFace (reconnaissance) d'OpenCV Zoo.

Ces modèles ne sont pas inclus dans le dépôt (fichiers binaires, non versionnés
par git — voir .gitignore) : ce script les télécharge dans `models/`.

Si le téléchargement échoue (pare-feu, proxy d'entreprise...), téléchargez-les
manuellement depuis les URLs ci-dessous et placez-les dans `models/` sous les
noms de fichiers indiqués.

Usage :
    python scripts/download_models.py
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"

MODELS = {
    "face_detection_yunet_2023mar.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/main/models/"
        "face_detection_yunet/face_detection_yunet_2023mar.onnx"
    ),
    "face_recognition_sface_2021dec.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/main/models/"
        "face_recognition_sface/face_recognition_sface_2021dec.onnx"
    ),
}


def main() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    failures = []

    for filename, url in MODELS.items():
        destination = MODELS_DIR / filename
        if destination.exists():
            print(f"[OK] {filename} déjà présent, téléchargement ignoré.")
            continue

        print(f"Téléchargement de {filename} depuis {url} ...")
        try:
            urllib.request.urlretrieve(url, destination)
        except Exception as exc:
            print(f"[ERREUR] Échec du téléchargement de {filename} : {exc}")
            print(f"  Téléchargez-le manuellement depuis {url}")
            print(f"  et placez-le dans {destination}")
            failures.append(filename)
            continue

        print(f"[OK] {filename} téléchargé vers {destination}")

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
