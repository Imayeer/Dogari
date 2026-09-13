"""Diagnostic ponctuel : pourquoi YuNet ne détecte-t-il aucun visage sur une image donnée ?

Script de débogage (pas une fonctionnalité permanente du projet) : teste la
détection sur l'image originale, puis sur des versions redimensionnées et
avec un seuil de confiance abaissé, pour isoler la cause d'un échec de
détection sur une photo réelle.

Usage :
    python scripts/debug_face_detection.py chemin/vers/photo.jpg
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dogari.core.config import settings  # noqa: E402


def try_detect(frame, input_size, score_threshold=0.9, label=""):
    detector = cv2.FaceDetectorYN.create(
        str(settings.yunet_model_path), "", input_size, score_threshold=score_threshold
    )
    _, faces = detector.detect(frame)
    count = 0 if faces is None else len(faces)
    best_score = max((f[-1] for f in faces), default=None) if faces is not None else None
    print(f"{label:45s} taille={input_size}  seuil={score_threshold}  visages_trouvés={count}  meilleur_score={best_score}")


def main() -> None:
    path = Path(sys.argv[1])
    frame = cv2.imread(str(path))
    if frame is None:
        print(f"Impossible de lire {path}")
        return

    height, width = frame.shape[:2]
    print(f"Image : {path.name}  —  résolution originale : {width}x{height}\n")

    # 1. Taille originale, seuil par défaut (0.9, comme dans le pipeline réel)
    try_detect(frame, (width, height), 0.9, "1. Taille originale, seuil 0.9 (défaut)")

    # 2. Taille originale, seuil abaissé (pour voir si une détection existe mais est filtrée)
    try_detect(frame, (width, height), 0.3, "2. Taille originale, seuil 0.3")

    # 3. Redimensionnée à 640px de large max, seuil par défaut
    scale = 640 / max(width, height)
    small = cv2.resize(frame, (int(width * scale), int(height * scale)))
    sh, sw = small.shape[:2]
    try_detect(small, (sw, sh), 0.9, "3. Redimensionnée ~640px, seuil 0.9")

    # 4. Redimensionnée, seuil abaissé
    try_detect(small, (sw, sh), 0.3, "4. Redimensionnée ~640px, seuil 0.3")


if __name__ == "__main__":
    main()
