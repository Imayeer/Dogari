"""Entraîne (fine-tune) un modèle YOLOv8 de détection d'armes sur un jeu de données local.

Ne télécharge ni n'héberge aucun modèle tiers : ce script entraîne localement
un modèle YOLOv8 léger (nano par défaut) à partir d'un jeu de données au
format YOLOv8 (un fichier `data.yaml` + dossiers `images/`/`labels/`), par
exemple téléchargé depuis Roboflow Universe (bouton "Download Dataset" →
format "YOLOv8", gratuit, sans clé API). Garde le fonctionnement 100% local
au moment de l'inférence, contrairement à une API tierce hébergée.

Nécessite `ultralytics` (voir requirements-weapon-detection.txt). Le modèle
de base (`yolov8n.pt`, pré-entraîné sur COCO) est téléchargé automatiquement
par `ultralytics` au premier lancement si absent.

⚠️ La qualité du modèle obtenu dépend entièrement du jeu de données utilisé :
ce script ne garantit aucune fiabilité particulière (voir l'avertissement sur
la détection d'armes dans le README). Évaluez le modèle sur des images de
test avant toute utilisation réelle.

Usage :
    python scripts/train_weapon_detector.py chemin/vers/data.yaml
    python scripts/train_weapon_detector.py chemin/vers/data.yaml --epochs 100 --imgsz 640
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("data_yaml", type=Path, help="Chemin vers data.yaml (jeu de données au format YOLOv8)")
    parser.add_argument("--epochs", type=int, default=50, help="Nombre d'itérations d'entraînement (défaut : 50)")
    parser.add_argument(
        "--model", default="yolov8n.pt", help="Modèle de base à affiner (défaut : yolov8n.pt, le plus léger)"
    )
    parser.add_argument("--imgsz", type=int, default=640, help="Taille des images d'entraînement (défaut : 640)")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("models/weapon_detection.pt"),
        help="Où copier les poids entraînés (défaut : models/weapon_detection.pt)",
    )
    args = parser.parse_args()

    if not args.data_yaml.is_file():
        print(f"[ERREUR] Fichier introuvable : {args.data_yaml}", file=sys.stderr)
        raise SystemExit(1)

    try:
        from ultralytics import YOLO
    except ImportError:
        print(
            "[ERREUR] Le paquet 'ultralytics' est requis. Installez-le avec "
            "`pip install -r requirements-weapon-detection.txt`.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    model = YOLO(args.model)
    results = model.train(data=str(args.data_yaml), epochs=args.epochs, imgsz=args.imgsz)

    best_weights = Path(results.save_dir) / "weights" / "best.pt"
    if not best_weights.is_file():
        print(f"[ERREUR] Poids entraînés introuvables à l'emplacement attendu : {best_weights}", file=sys.stderr)
        raise SystemExit(1)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(best_weights, args.output)

    print(f"\nModèle entraîné copié vers {args.output}")
    print("Résultats détaillés (courbes, matrice de confusion) dans :", results.save_dir)
    print("\nPour l'activer :")
    print("  DOGARI_WEAPON_DETECTION_ENABLED=true python -m dogari.web.app")


if __name__ == "__main__":
    main()
