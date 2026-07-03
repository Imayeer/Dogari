"""Évalue la précision du système de reconnaissance faciale sur un jeu de test étiqueté.

Utile pour mesurer l'exactitude réelle du modèle (indispensable pour un
rapport PFE/Master) et pour choisir la valeur de `DOGARI_RECOGNITION_TOLERANCE`
la mieux adaptée à vos données.

Structure attendue du dossier de jeu de test :

    <dataset>/
    ├── gallery/            # images de référence, une par utilisateur connu
    │   ├── alice/*.jpg
    │   └── bob/*.jpg
    └── probes/             # images à tester
        ├── alice/*.jpg     # doivent être reconnues comme "alice"
        ├── bob/*.jpg       # doivent être reconnues comme "bob"
        └── unknown/*.jpg   # doivent être rejetées (personnes non enregistrées)

Usage :

    python scripts/evaluate_recognition.py data/evaluation
    python scripts/evaluate_recognition.py data/evaluation --tolerance 0.5
    python scripts/evaluate_recognition.py data/evaluation --sweep
    python scripts/evaluate_recognition.py data/evaluation --csv results.csv
"""

from __future__ import annotations

import argparse
import csv as csv_module
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# Permet d'exécuter ce script directement sans installation préalable du paquet.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dogari.core.config import settings
from dogari.storage.models import User, encode_embedding
from dogari.vision.recognizer import FaceRecognizer

UNKNOWN_LABEL = "unknown"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}
DEFAULT_SWEEP_TOLERANCES = [round(0.3 + 0.05 * i, 2) for i in range(9)]


@dataclass
class ProbeResult:
    """Résultat de la reconnaissance pour une image de test."""

    image_path: str
    true_label: str
    predicted_label: str | None
    similarity_score: float | None


@dataclass
class EvaluationSummary:
    """Agrège les résultats d'une évaluation et calcule les métriques standard."""

    results: list[ProbeResult] = field(default_factory=list)

    @property
    def genuine_attempts(self) -> list[ProbeResult]:
        """Tentatives d'une personne réellement enregistrée dans la galerie."""
        return [r for r in self.results if r.true_label != UNKNOWN_LABEL]

    @property
    def impostor_attempts(self) -> list[ProbeResult]:
        """Tentatives d'une personne non enregistrée (inconnue)."""
        return [r for r in self.results if r.true_label == UNKNOWN_LABEL]

    @property
    def true_accepts(self) -> list[ProbeResult]:
        return [r for r in self.genuine_attempts if r.predicted_label == r.true_label]

    @property
    def false_rejects(self) -> list[ProbeResult]:
        return [r for r in self.genuine_attempts if r.predicted_label != r.true_label]

    @property
    def true_rejects(self) -> list[ProbeResult]:
        return [r for r in self.impostor_attempts if r.predicted_label is None]

    @property
    def false_accepts(self) -> list[ProbeResult]:
        return [r for r in self.impostor_attempts if r.predicted_label is not None]

    @property
    def accuracy(self) -> float:
        if not self.results:
            return 0.0
        correct = len(self.true_accepts) + len(self.true_rejects)
        return correct / len(self.results)

    @property
    def far(self) -> float:
        """False Acceptance Rate : proportion d'imposteurs acceptés à tort."""
        if not self.impostor_attempts:
            return 0.0
        return len(self.false_accepts) / len(self.impostor_attempts)

    @property
    def frr(self) -> float:
        """False Rejection Rate : proportion d'utilisateurs légitimes refusés à tort."""
        if not self.genuine_attempts:
            return 0.0
        return len(self.false_rejects) / len(self.genuine_attempts)


def evaluate_probes(
    gallery: list[User],
    probes: list[tuple[str, np.ndarray, str]],
    tolerance: float,
) -> EvaluationSummary:
    """Exécute la reconnaissance sur chaque probe et calcule les métriques.

    `probes` est une liste de (label_attendu, embedding, chemin_image). Séparée
    du chargement des images pour rester testable sans dépendance caméra/dlib.
    """
    recognizer = FaceRecognizer(gallery, tolerance=tolerance)
    summary = EvaluationSummary()
    for true_label, embedding, image_path in probes:
        match = recognizer.identify(embedding)
        summary.results.append(
            ProbeResult(
                image_path=image_path,
                true_label=true_label,
                predicted_label=match.user.full_name if match.matched else None,
                similarity_score=match.score,
            )
        )
    return summary


def _iter_images(directory: Path):
    for path in sorted(directory.iterdir()):
        if path.suffix.lower() in IMAGE_EXTENSIONS:
            yield path


def load_gallery(gallery_dir: Path) -> list[User]:
    """Construit la galerie d'utilisateurs connus à partir d'un dossier d'images.

    Chaque sous-dossier de `gallery_dir` représente une identité ; l'embedding
    moyen de ses images de référence est utilisé pour plus de robustesse.
    """
    from dogari.vision.detector import detect_single_face
    from dogari.vision.embeddings import generate_embedding
    import cv2

    gallery: list[User] = []
    for index, person_dir in enumerate(sorted(p for p in gallery_dir.iterdir() if p.is_dir()), start=1):
        embeddings = []
        for image_path in _iter_images(person_dir):
            frame = cv2.imread(str(image_path))
            if frame is None:
                print(f"[AVERTISSEMENT] Image illisible ignorée : {image_path}")
                continue
            face_location = detect_single_face(frame)
            if face_location is None:
                print(f"[AVERTISSEMENT] Aucun visage détecté, image ignorée : {image_path}")
                continue
            embeddings.append(generate_embedding(frame, face_location))
        if not embeddings:
            print(f"[AVERTISSEMENT] Aucune image exploitable pour '{person_dir.name}', utilisateur ignoré.")
            continue
        average_embedding = np.mean(embeddings, axis=0)
        gallery.append(
            User(
                id=index,
                full_name=person_dir.name,
                role=None,
                status="active",
                face_image_path=None,
                face_embedding=encode_embedding(average_embedding),
                created_at=None,
            )
        )
    return gallery


def load_probes(probes_dir: Path) -> list[tuple[str, np.ndarray, str]]:
    """Charge les images de test et génère leur embedding, groupées par label attendu."""
    from dogari.vision.detector import detect_single_face
    from dogari.vision.embeddings import generate_embedding
    import cv2

    probes: list[tuple[str, np.ndarray, str]] = []
    for label_dir in sorted(p for p in probes_dir.iterdir() if p.is_dir()):
        for image_path in _iter_images(label_dir):
            frame = cv2.imread(str(image_path))
            if frame is None:
                print(f"[AVERTISSEMENT] Image illisible ignorée : {image_path}")
                continue
            face_location = detect_single_face(frame)
            if face_location is None:
                print(f"[AVERTISSEMENT] Aucun visage détecté, image ignorée : {image_path}")
                continue
            embedding = generate_embedding(frame, face_location)
            probes.append((label_dir.name, embedding, str(image_path)))
    return probes


def print_report(summary: EvaluationSummary, tolerance: float) -> None:
    print(f"\n=== Résultats (tolérance = {tolerance:.2f}) ===")
    print(f"Tentatives légitimes (genuine)  : {len(summary.genuine_attempts)}")
    print(f"  Acceptées correctement (True Accept) : {len(summary.true_accepts)}")
    print(f"  Refusées à tort (False Reject)       : {len(summary.false_rejects)}")
    print(f"Tentatives imposteurs/inconnus  : {len(summary.impostor_attempts)}")
    print(f"  Refusées correctement (True Reject)  : {len(summary.true_rejects)}")
    print(f"  Acceptées à tort (False Accept)      : {len(summary.false_accepts)}")
    print(f"\nExactitude globale (accuracy) : {summary.accuracy:.2%}")
    print(f"Taux de faux positifs (FAR)    : {summary.far:.2%}")
    print(f"Taux de faux négatifs (FRR)    : {summary.frr:.2%}")

    if summary.false_rejects or summary.false_accepts:
        print("\nErreurs détaillées :")
        for r in summary.false_rejects:
            print(
                f"  [FAUX REJET]         {r.image_path} "
                f"(attendu: {r.true_label}, obtenu: {r.predicted_label}, score: {r.similarity_score})"
            )
        for r in summary.false_accepts:
            print(
                f"  [FAUSSE ACCEPTATION] {r.image_path} "
                f"(attendu: inconnu, obtenu: {r.predicted_label}, score: {r.similarity_score})"
            )


def write_csv(summary: EvaluationSummary, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv_module.writer(csv_file)
        writer.writerow(["image_path", "true_label", "predicted_label", "similarity_score", "correct"])
        for r in summary.results:
            expected_predicted = None if r.true_label == UNKNOWN_LABEL else r.true_label
            correct = r.predicted_label == expected_predicted
            writer.writerow([r.image_path, r.true_label, r.predicted_label or "", r.similarity_score, correct])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Évalue la précision de la reconnaissance faciale de Dogari sur un jeu de test étiqueté."
    )
    parser.add_argument("dataset", type=Path, help="Dossier contenant les sous-dossiers gallery/ et probes/")
    parser.add_argument(
        "--tolerance",
        type=float,
        default=None,
        help="Seuil de tolérance à tester (défaut : DOGARI_RECOGNITION_TOLERANCE)",
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="Teste plusieurs seuils (0.30 à 0.70) pour trouver le meilleur compromis FAR/FRR",
    )
    parser.add_argument("--csv", type=Path, default=None, help="Exporte les résultats détaillés au format CSV")
    args = parser.parse_args()

    gallery_dir = args.dataset / "gallery"
    probes_dir = args.dataset / "probes"
    if not gallery_dir.is_dir() or not probes_dir.is_dir():
        parser.error(f"'{args.dataset}' doit contenir des sous-dossiers 'gallery/' et 'probes/'.")

    print(f"Chargement de la galerie depuis {gallery_dir} ...")
    gallery = load_gallery(gallery_dir)
    print(f"{len(gallery)} utilisateur(s) chargé(s) : {', '.join(u.full_name for u in gallery) or '(aucun)'}")

    print(f"Chargement des images de test depuis {probes_dir} ...")
    raw_probes = load_probes(probes_dir)
    print(f"{len(raw_probes)} image(s) de test chargée(s).")

    if not gallery or not raw_probes:
        print("\nRien à évaluer : vérifiez le contenu de gallery/ et probes/.")
        return

    if args.sweep:
        print("\n--- Balayage des seuils de tolérance ---")
        print(f"{'Tolérance':>10} {'Accuracy':>10} {'FAR':>8} {'FRR':>8}")
        for tolerance in DEFAULT_SWEEP_TOLERANCES:
            summary = evaluate_probes(gallery, raw_probes, tolerance)
            print(f"{tolerance:>10.2f} {summary.accuracy:>9.1%} {summary.far:>7.1%} {summary.frr:>7.1%}")
        return

    tolerance = args.tolerance if args.tolerance is not None else settings.recognition_tolerance
    summary = evaluate_probes(gallery, raw_probes, tolerance)
    print_report(summary, tolerance)

    if args.csv:
        write_csv(summary, args.csv)
        print(f"\nRésultats détaillés exportés vers {args.csv}")


if __name__ == "__main__":
    main()
