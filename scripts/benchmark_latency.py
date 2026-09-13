"""Mesure la latence du pipeline de reconnaissance faciale de Dogari.

Sert à documenter H2 (temps de décision suffisamment faible pour un usage
pratique) : mesure séparément le temps de détection (YuNet), le temps
d'extraction d'embedding (SFace) et le temps total, répétés sur N images,
avec moyenne, médiane et 95e percentile.

Utilisation :
    python scripts/benchmark_latency.py chemin/vers/une_image.jpg --runs 50
    python scripts/benchmark_latency.py chemin/vers/un_dossier_dimages/ --runs 50 --csv latence.csv

Si `psutil` est installé, la mémoire résidente du processus est aussi
rapportée avant et après la boucle de mesure (installation optionnelle :
`pip install psutil`, non ajoutée aux dépendances du projet pour ne pas
alourdir le déploiement embarqué).
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
import time
from pathlib import Path

import cv2
import numpy as np

from dogari.vision.detector import detect_single_face
from dogari.vision.embeddings import generate_embedding

try:
    import psutil

    _PROCESS = psutil.Process()
except ImportError:
    psutil = None
    _PROCESS = None


def _load_images(path: Path) -> list[tuple[str, np.ndarray]]:
    if path.is_dir():
        extensions = {".jpg", ".jpeg", ".png"}
        files = sorted(p for p in path.iterdir() if p.suffix.lower() in extensions)
    else:
        files = [path]

    images = []
    for file in files:
        frame = cv2.imread(str(file))
        if frame is None:
            print(f"[ATTENTION] Impossible de lire {file}, ignorée.")
            continue
        images.append((file.name, frame))

    if not images:
        print("Aucune image valide trouvée.")
        sys.exit(1)

    return images


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(pct / 100 * (len(ordered) - 1))))
    return ordered[index]


def _summary(label: str, values_ms: list[float]) -> dict:
    return {
        "etape": label,
        "n": len(values_ms),
        "moyenne_ms": round(statistics.mean(values_ms), 2) if values_ms else float("nan"),
        "mediane_ms": round(statistics.median(values_ms), 2) if values_ms else float("nan"),
        "p95_ms": round(_percentile(values_ms, 95), 2),
        "min_ms": round(min(values_ms), 2) if values_ms else float("nan"),
        "max_ms": round(max(values_ms), 2) if values_ms else float("nan"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", type=Path, help="Image unique ou dossier d'images de test")
    parser.add_argument("--runs", type=int, default=30, help="Nombre de répétitions par image (défaut 30)")
    parser.add_argument("--csv", type=Path, default=None, help="Chemin d'export CSV du résumé")
    args = parser.parse_args()

    images = _load_images(args.images)
    print(f"{len(images)} image(s) chargée(s), {args.runs} répétition(s) chacune.\n")

    detection_ms: list[float] = []
    embedding_ms: list[float] = []
    total_ms: list[float] = []
    no_face_count = 0

    if _PROCESS:
        mem_before = _PROCESS.memory_info().rss / (1024 * 1024)

    for name, frame in images:
        for _ in range(args.runs):
            t0 = time.perf_counter()
            face = detect_single_face(frame)
            t1 = time.perf_counter()

            if face is None:
                no_face_count += 1
                continue

            _ = generate_embedding(frame, face)
            t2 = time.perf_counter()

            detection_ms.append((t1 - t0) * 1000)
            embedding_ms.append((t2 - t1) * 1000)
            total_ms.append((t2 - t0) * 1000)

        print(f"[OK] {name} : traité.")

    if no_face_count:
        print(f"\n[ATTENTION] Aucun visage détecté sur {no_face_count} passage(s) (exclus des mesures).")

    rows = [
        _summary("detection_yunet", detection_ms),
        _summary("embedding_sface", embedding_ms),
        _summary("total_decision", total_ms),
    ]

    print("\nRésumé (millisecondes) :")
    print(f"{'Étape':<20}{'n':>6}{'Moyenne':>10}{'Médiane':>10}{'P95':>10}{'Min':>10}{'Max':>10}")
    for row in rows:
        print(
            f"{row['etape']:<20}{row['n']:>6}{row['moyenne_ms']:>10}"
            f"{row['mediane_ms']:>10}{row['p95_ms']:>10}{row['min_ms']:>10}{row['max_ms']:>10}"
        )

    if _PROCESS:
        mem_after = _PROCESS.memory_info().rss / (1024 * 1024)
        print(f"\nMémoire résidente du processus : {mem_before:.1f} Mo avant, {mem_after:.1f} Mo après.")
    else:
        print("\n(psutil non installé : mesure mémoire non disponible. `pip install psutil` pour l'obtenir.)")

    if args.csv:
        with args.csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nRésumé exporté vers {args.csv}")


if __name__ == "__main__":
    main()
