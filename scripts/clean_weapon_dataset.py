"""Vérifie et nettoie un jeu de données YOLOv8 avant l'entraînement du détecteur d'armes.

Analyse chaque split (train/valid/test) déclaré dans un `data.yaml` au format
YOLOv8 (images/ + labels/) et détecte :

- les images corrompues ou illisibles ;
- les images sans fichier de labels correspondant, et les labels orphelins
  (sans image associée) ;
- les fichiers de labels malformés (nombre de champs incorrect, identifiant
  de classe hors de la plage déclarée dans `data.yaml`, coordonnées hors de
  l'intervalle [0, 1]) ;
- les images strictement dupliquées (même contenu binaire) ;

et affiche un rapport, ainsi qu'un décompte d'instances par classe (pour
repérer un déséquilibre flagrant).

Par défaut, le script ne modifie rien (mode rapport seul). Avec `--fix`, les
fichiers problématiques (image + label associés) sont déplacés vers un
dossier `_quarantaine/` à la racine du jeu de données plutôt que supprimés
définitivement, pour rester réversible.

Usage :
    python scripts/clean_weapon_dataset.py chemin/vers/data.yaml
    python scripts/clean_weapon_dataset.py chemin/vers/data.yaml --fix
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def _load_data_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError:
        print(
            "[ERREUR] Le paquet 'pyyaml' est requis (installé automatiquement avec "
            "`pip install -r requirements-weapon-detection.txt`).",
            file=sys.stderr,
        )
        raise SystemExit(1)

    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _resolve_split_dir(data_yaml_path: Path, split_value: str) -> Path:
    """Résout un chemin d'images de split (souvent relatif au data.yaml)."""
    candidate = Path(split_value)
    if not candidate.is_absolute():
        candidate = (data_yaml_path.parent / candidate).resolve()
    return candidate


def _label_path_for_image(image_path: Path) -> Path:
    """Convention YOLOv8 : labels/ en miroir de images/, extension .txt."""
    parts = list(image_path.parts)
    for index, part in enumerate(parts):
        if part == "images":
            parts[index] = "labels"
            break
    return Path(*parts).with_suffix(".txt")


def _image_path_for_label(label_path: Path, images_dir: Path) -> Path | None:
    for ext in IMAGE_EXTENSIONS:
        candidate = images_dir / (label_path.stem + ext)
        if candidate.is_file():
            return candidate
    return None


def _is_valid_image(path: Path) -> bool:
    import cv2  # dépendance déjà requise par le reste du projet

    return cv2.imread(str(path)) is not None


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_label_file(label_path: Path, num_classes: int) -> list[str]:
    """Retourne la liste des lignes invalides (description) d'un fichier de labels."""
    problems = []
    with label_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            fields = line.split()
            if len(fields) != 5:
                problems.append(f"ligne {line_number} : {len(fields)} champs (5 attendus)")
                continue
            class_id_raw, *coords = fields
            try:
                class_id = int(class_id_raw)
            except ValueError:
                problems.append(f"ligne {line_number} : identifiant de classe non entier ({class_id_raw!r})")
                continue
            if not 0 <= class_id < num_classes:
                problems.append(f"ligne {line_number} : classe {class_id} hors plage (0-{num_classes - 1})")
            for value in coords:
                try:
                    parsed = float(value)
                except ValueError:
                    problems.append(f"ligne {line_number} : coordonnée non numérique ({value!r})")
                    continue
                if not 0.0 <= parsed <= 1.0:
                    problems.append(f"ligne {line_number} : coordonnée hors de [0, 1] ({parsed})")
    return problems


def _quarantine(paths: list[Path], dataset_root: Path) -> None:
    quarantine_dir = dataset_root / "_quarantaine"
    for path in paths:
        if not path.is_file():
            continue
        relative = path.relative_to(dataset_root) if dataset_root in path.parents else path.name
        destination = quarantine_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(destination))


def clean_split(images_dir: Path, num_classes: int, dataset_root: Path, fix: bool) -> Counter:
    """Analyse un split (dossier images/) et retourne un compteur d'instances par classe."""
    if not images_dir.is_dir():
        print(f"[AVERTISSEMENT] Dossier introuvable, ignoré : {images_dir}")
        return Counter()

    labels_dir = images_dir.parent / "labels"
    image_paths = sorted(p for p in images_dir.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS)
    label_paths = sorted(labels_dir.glob("*.txt")) if labels_dir.is_dir() else []

    corrupted: list[Path] = []
    missing_label: list[Path] = []
    orphan_labels: list[Path] = []
    malformed: dict[Path, list[str]] = {}
    # Association image <-> label pour chaque fichier problématique, afin de mettre les
    # deux en quarantaine ensemble et ne jamais laisser le dataset plus incohérent qu'avant.
    label_for_image: dict[Path, Path] = {}
    class_counts: Counter = Counter()
    hashes: dict[str, list[Path]] = defaultdict(list)

    for image_path in image_paths:
        label_path = _label_path_for_image(image_path)
        if label_path.is_file():
            label_for_image[image_path] = label_path

        if not _is_valid_image(image_path):
            corrupted.append(image_path)
            continue

        if not label_path.is_file():
            missing_label.append(image_path)
        else:
            problems = _validate_label_file(label_path, num_classes)
            if problems:
                malformed[label_path] = problems
            else:
                with label_path.open(encoding="utf-8") as handle:
                    for line in handle:
                        if line.strip():
                            class_counts[int(line.split()[0])] += 1

        hashes[_file_hash(image_path)].append(image_path)

    known_images = {p.stem for p in image_paths}
    for label_path in label_paths:
        if label_path.stem not in known_images:
            orphan_labels.append(label_path)

    duplicates = [group for group in hashes.values() if len(group) > 1]

    print(f"\n=== {images_dir} ===")
    print(f"Images : {len(image_paths)}  |  Labels : {len(label_paths)}")
    print(f"  Corrompues            : {len(corrupted)}")
    print(f"  Sans label associé    : {len(missing_label)}")
    print(f"  Labels orphelins      : {len(orphan_labels)}")
    print(f"  Labels malformés      : {len(malformed)}")
    print(f"  Groupes de doublons   : {len(duplicates)} ({sum(len(g) - 1 for g in duplicates)} images en trop)")

    for path in corrupted[:5]:
        print(f"    - corrompue : {path}")
    for path in missing_label[:5]:
        print(f"    - sans label : {path}")
    for path in orphan_labels[:5]:
        print(f"    - orphelin : {path}")
    for label_path, problems in list(malformed.items())[:5]:
        print(f"    - malformé : {label_path} ({problems[0]})")
    for group in duplicates[:5]:
        print(f"    - doublons : {[str(p) for p in group]}")

    if fix:
        image_for_label = {label: image for image, label in label_for_image.items()}
        to_quarantine: set[Path] = set(orphan_labels)

        for image_path in corrupted + missing_label:
            to_quarantine.add(image_path)
            if image_path in label_for_image:
                to_quarantine.add(label_for_image[image_path])

        for label_path in malformed:
            to_quarantine.add(label_path)
            if label_path in image_for_label:
                to_quarantine.add(image_for_label[label_path])

        for group in duplicates:
            for image_path in group[1:]:  # garde le premier, met le reste en quarantaine
                to_quarantine.add(image_path)
                if image_path in label_for_image:
                    to_quarantine.add(label_for_image[image_path])

        if to_quarantine:
            _quarantine(sorted(to_quarantine), dataset_root)
            print(f"  → {len(to_quarantine)} fichier(s) déplacé(s) vers {dataset_root / '_quarantaine'}")

    return class_counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("data_yaml", type=Path, help="Chemin vers data.yaml (jeu de données au format YOLOv8)")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Déplace les fichiers problématiques vers _quarantaine/ au lieu de se contenter d'un rapport",
    )
    args = parser.parse_args()

    if not args.data_yaml.is_file():
        print(f"[ERREUR] Fichier introuvable : {args.data_yaml}", file=sys.stderr)
        raise SystemExit(1)

    config = _load_data_yaml(args.data_yaml)
    names = config.get("names", [])
    num_classes = config.get("nc", len(names))
    dataset_root = args.data_yaml.parent.resolve()

    print(f"Classes ({num_classes}) : {names}")

    total_class_counts: Counter = Counter()
    for split in ("train", "val", "valid", "test"):
        if split not in config:
            continue
        images_dir = _resolve_split_dir(args.data_yaml, config[split])
        total_class_counts.update(clean_split(images_dir, num_classes, dataset_root, args.fix))

    print("\n=== Répartition des instances par classe (tous splits) ===")
    for class_id, count in sorted(total_class_counts.items()):
        label = names[class_id] if class_id < len(names) else f"classe {class_id}"
        print(f"  {label:20s} : {count}")

    if not args.fix:
        print("\nMode rapport seul (aucun fichier modifié). Relancez avec --fix pour corriger.")


if __name__ == "__main__":
    main()
