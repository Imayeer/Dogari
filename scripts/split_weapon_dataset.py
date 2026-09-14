"""Prépare un jeu de données plat (images/ + labels/) au format attendu par
`scripts/clean_weapon_dataset.py` et `scripts/train_weapon_detector.py` :
un split train/val avec `data.yaml`.

Certains jeux de données téléchargés (ex. Kaggle) livrent un unique dossier
`images/` + `labels/` sans séparation train/val, contrairement à un export
Roboflow qui inclut déjà `data.yaml`. Ce script comble cet écart : il répartit
les paires image/label en deux sous-ensembles, les copie (les fichiers
d'origine ne sont jamais modifiés ni déplacés) dans une nouvelle arborescence
YOLOv8 standard, et génère le `data.yaml` correspondant.

Par défaut, le split se fait par image individuelle. Avec `--group-by-scene`,
il se fait par GROUPE : les images dont le nom suit le motif
`<groupe>_<numéro>` (ex. `Scene1_1.png`, `Scene1_2.png`, ..., typique de
frames extraites d'une vidéo) sont alors toujours affectées ensemble au même
split. C'est important pour un jeu de données de ce type : un split par image
individuelle ferait fuiter des frames quasi identiques (même scène, même
arrière-plan) entre train et val, ce qui gonflerait artificiellement les
métriques de validation (le modèle serait évalué sur des images presque déjà
vues à l'entraînement, pas sur un vrai test d'indépendance).

⚠️ `--group-by-scene` n'est PAS le comportement par défaut : le motif
`<préfixe>_<numéro>` est aussi celui de conventions de nommage photo
courantes et sans rapport (`IMG_0162.jpg`, `DSC_1024.jpg`, ...), où le
préfixe est constant sur tout un dossier de photos indépendantes. L'activer
sur un tel dossier grouperait à tort toutes les photos ensemble et casserait
le split (tout irait dans un seul sous-ensemble). N'utilisez ce drapeau que
si vous savez que le nom de fichier encode une scène/séquence source.

Usage :
    python scripts/split_weapon_dataset.py chemin/vers/Dataset --output dataset_split
    python scripts/split_weapon_dataset.py chemin/vers/Dataset --output dataset_split \
        --val-ratio 0.2 --names person weapon
    python scripts/split_weapon_dataset.py chemin/vers/Dataset --output dataset_split \
        --group-by-scene
"""

from __future__ import annotations

import argparse
import random
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
_GROUP_PATTERN = re.compile(r"^(.*)_\d+$")


def _group_key(stem: str, group_by_scene: bool) -> str:
    """Extrait le préfixe de groupe (ex. 'Scene1' pour 'Scene1_12') si
    `group_by_scene` est activé et que le motif <groupe>_<numéro> est détecté ;
    sinon chaque image forme son propre groupe (nom complet)."""
    if not group_by_scene:
        return stem
    match = _GROUP_PATTERN.match(stem)
    return match.group(1) if match else stem


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
    parser.add_argument(
        "--group-by-scene",
        action="store_true",
        help=(
            "Groupe les images par préfixe <groupe>_<numéro> (ex. Scene1_1, Scene1_2, ...) pour que toutes "
            "les frames d'une même scène/séquence restent dans le même split. À utiliser uniquement si le "
            "nom de fichier encode une scène source (voir avertissement en tête de ce script) — désactivé "
            "par défaut, sinon un dossier de photos 'IMG_xxxx' serait groupé à tort en un seul bloc."
        ),
    )
    args = parser.parse_args()

    pairs = _find_pairs(args.source)
    if not pairs:
        print("[ERREUR] Aucune paire image/label trouvée.", file=sys.stderr)
        raise SystemExit(1)

    groups: dict[str, list[tuple[Path, Path]]] = defaultdict(list)
    for image_path, label_path in pairs:
        groups[_group_key(image_path.stem, args.group_by_scene)].append((image_path, label_path))

    group_keys = list(groups.keys())
    random.Random(args.seed).shuffle(group_keys)

    target_val = len(pairs) * args.val_ratio
    val_pairs: list[tuple[Path, Path]] = []
    train_pairs: list[tuple[Path, Path]] = []
    val_groups: list[str] = []
    for key in group_keys:
        if len(val_pairs) < target_val:
            val_pairs.extend(groups[key])
            val_groups.append(key)
        else:
            train_pairs.extend(groups[key])
    if not val_pairs:  # au moins un groupe en val, même si target_val arrondit à 0
        key = group_keys[0]
        val_pairs = list(groups[key])
        val_groups = [key]
        train_pairs = [pair for k in group_keys[1:] for pair in groups[k]]

    if args.group_by_scene and len(groups) > 1:
        print(f"{len(groups)} groupe(s) détecté(s) (ex. frames vidéo par scène) : {sorted(groups)}")
        print(f"Groupe(s) en validation : {sorted(val_groups)} (jamais mélangés avec train)")

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
        # `path:` absolu nécessaire : sans lui, `ultralytics` résout train/val
        # relativement à son dossier global de datasets configuré
        # (`yolo settings` / settings.json), pas à l'emplacement de ce data.yaml.
        handle.write(f"path: {args.output.resolve().as_posix()}\n")
        handle.write("train: train/images\n")
        handle.write("val: val/images\n")
        handle.write(f"nc: {len(args.names)}\n")
        handle.write(f"names: {args.names}\n")

    print(f"Split terminé : {len(train_pairs)} train / {len(val_pairs)} val (sur {len(pairs)} paires trouvées).")
    print(f"data.yaml généré : {data_yaml}")
    print(f"\nProchaine étape :\n  python scripts/clean_weapon_dataset.py {data_yaml}")


if __name__ == "__main__":
    main()
