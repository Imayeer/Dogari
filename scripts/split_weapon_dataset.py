"""Prépare un jeu de données plat (images/ + labels/) au format attendu par
`scripts/clean_weapon_dataset.py` et `scripts/train_weapon_detector.py` :
un split train/val avec `data.yaml`.

Certains jeux de données téléchargés (ex. Kaggle) livrent un unique dossier
`images/` + `labels/` sans séparation train/val, contrairement à un export
Roboflow qui inclut déjà `data.yaml`. Ce script comble cet écart : il répartit
aléatoirement les paires image/label en deux sous-ensembles, les copie (les
fichiers d'origine ne sont jamais modifiés ni déplacés) dans une nouvelle
arborescence YOLOv8 standard, et génère le `data.yaml` correspondant.

Usage :
    python scripts/split_weapon_dataset.py chemin/vers/Dataset --output dataset_split
    python scripts/split_weapon_dataset.py chemin/vers/Dataset --output dataset_split \
        --val-ratio 0.2 --names person weapon
"""

from __future__ import annotations

import argparse
import random
import shutil
import sys
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def _find_pairs(source: Path) -> list[tuple[Path, Path]]:
    images_dir = source / "images"
    labels_dir = source / "labels"
    if not images_dir.is_dir() or not labels_dir.is_dir():
        print(f"[ERREUR] Attendu {images_dir} et {labels_dir} (structure images/ + labels/).", file=sys.stderr)
        raise SystemExit(1)

    pairs = []
    skipped = 0
    for image_path in sorted(images_dir.iterdir()):
        if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        label_path = labels_dir / (image_path.stem + ".txt")
        if not label_path.is_file():
            skipped += 1
            continue
        pairs.append((image_path, label_path))

    if skipped:
        print(f"[ATTENTION] {skipped} image(s) sans label associé, ignorée(s).")
    return pairs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path, help="Dossier contenant images/ et labels/ (dataset plat)")
    parser.add_argument("--output", type=Path, default=Path("dataset_split"), help="Dossier de sortie à créer")
    parser.add_argument("--val-ratio", type=float, default=0.2, help="Proportion pour la validation (défaut : 0.2)")
    parser.add_argument("--seed", type=int, default=42, help="Graine aléatoire, pour un split reproductible")
    parser.add_argument(
        "--names", nargs="+", default=["person", "weapon"], help="Noms des classes, dans l'ordre des identifiants"
    )
    args = parser.parse_args()

    pairs = _find_pairs(args.source)
    if not pairs:
        print("[ERREUR] Aucune paire image/label trouvée.", file=sys.stderr)
        raise SystemExit(1)

    random.Random(args.seed).shuffle(pairs)
    n_val = max(1, round(len(pairs) * args.val_ratio))
    val_pairs = pairs[:n_val]
    train_pairs = pairs[n_val:]

    # Convention `<split>/images/` + `<split>/labels/` (dossiers frères sous chaque
    # split), celle attendue par `clean_weapon_dataset.py`
    # (labels_dir = images_dir.parent / "labels").
    for split_name, split_pairs in (("train", train_pairs), ("val", val_pairs)):
        images_out = args.output / split_name / "images"
        labels_out = args.output / split_name / "labels"
        images_out.mkdir(parents=True, exist_ok=True)
        labels_out.mkdir(parents=True, exist_ok=True)
        for image_path, label_path in split_pairs:
            shutil.copy(image_path, images_out / image_path.name)
            shutil.copy(label_path, labels_out / label_path.name)

    data_yaml = args.output / "data.yaml"
    with data_yaml.open("w", encoding="utf-8") as handle:
        handle.write("train: train/images\n")
        handle.write("val: val/images\n")
        handle.write(f"nc: {len(args.names)}\n")
        handle.write(f"names: {args.names}\n")

    print(f"Split terminé : {len(train_pairs)} train / {len(val_pairs)} val (sur {len(pairs)} paires trouvées).")
    print(f"data.yaml généré : {data_yaml}")
    print(f"\nProchaine étape :\n  python scripts/clean_weapon_dataset.py {data_yaml}")


if __name__ == "__main__":
    main()
