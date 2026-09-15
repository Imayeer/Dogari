"""Protocole expérimental de test de la détection de vivacité (H3).

Compare trois scénarios sur plusieurs essais chacun : visage réel, photo
imprimée présentée à la caméra, photo affichée sur écran (téléphone ou
ordinateur). Calcule le taux de détection d'attaque (ADR, essais "photo"
correctement rejetés) et le taux de faux rejet sur visage réel (essais
"réel" incorrectement rejetés comme non vivants).

Utilisation :
    python scripts/test_liveness_scenarios.py --trials 10 --csv liveness.csv

Le script est interactif : il vous demande de vous positionner (ou de
positionner la photo) avant chaque essai, puis capture une rafale via la
caméra configurée (DOGARI_CAMERA_SOURCE), exactement comme le ferait
l'application en conditions réelles.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from dogari.core.config import settings
from dogari.core.exceptions import CameraError
from dogari.vision.camera import Camera
from dogari.vision.detector import detect_single_face
from dogari.vision.liveness import check_liveness

SCENARIOS = [
    ("reel", "Positionnez-vous devant la caméra, visage réel"),
    ("photo_imprimee", "Présentez une photo IMPRIMÉE de votre visage devant la caméra"),
    ("photo_ecran", "Affichez une photo de votre visage sur un écran (téléphone/PC) devant la caméra"),
]


def _run_trial(camera: Camera) -> dict | None:
    frames = camera.capture_burst(settings.liveness_frame_count, settings.liveness_capture_interval)
    face = detect_single_face(frames[-1])
    if face is None:
        print("  [ATTENTION] Aucun visage détecté sur cet essai, ignoré (repositionnez-vous).")
        return None
    result = check_liveness(frames, face)
    return {"is_live": result.is_live, "motion_score": round(result.motion_score, 4)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=10, help="Essais par scénario (défaut 10)")
    parser.add_argument("--csv", type=Path, default=None, help="Chemin d'export CSV détaillé")
    args = parser.parse_args()

    print(f"Seuil configuré (DOGARI_LIVENESS_MOTION_THRESHOLD) : {settings.liveness_motion_threshold}")
    print(f"Rafale : {settings.liveness_frame_count} images, intervalle {settings.liveness_capture_interval}s\n")

    try:
        camera = Camera().open()
    except CameraError as exc:
        print(f"[ERREUR] {exc}")
        sys.exit(1)

    rows = []
    try:
        for scenario_id, instruction in SCENARIOS:
            print(f"\n=== Scénario : {scenario_id} ===")
            print(instruction)
            for trial in range(1, args.trials + 1):
                input(f"  Essai {trial}/{args.trials} : appuyez sur Entrée quand prêt...")
                outcome = _run_trial(camera)
                if outcome is None:
                    continue
                verdict = "vivant" if outcome["is_live"] else "rejeté (non vivant)"
                print(f"  -> motion_score={outcome['motion_score']}, verdict={verdict}")
                rows.append({"scenario": scenario_id, "essai": trial, **outcome})
    finally:
        camera.release()

    if not rows:
        print("\nAucun essai valide enregistré.")
        return

    print("\n=== Résumé ===")
    for scenario_id, _ in SCENARIOS:
        scenario_rows = [r for r in rows if r["scenario"] == scenario_id]
        if not scenario_rows:
            print(f"{scenario_id}: aucun essai valide")
            continue
        n = len(scenario_rows)
        live_count = sum(1 for r in scenario_rows if r["is_live"])
        if scenario_id == "reel":
            print(f"{scenario_id}: {live_count}/{n} correctement acceptés comme vivants "
                  f"(faux rejet réel = {n - live_count}/{n})")
        else:
            rejected = n - live_count
            print(f"{scenario_id}: {rejected}/{n} correctement rejetés comme non vivants "
                  f"(ADR = {rejected}/{n}, attaques acceptées à tort = {live_count}/{n})")

    if args.csv:
        with args.csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["scenario", "essai", "is_live", "motion_score"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nDétail exporté vers {args.csv}")


if __name__ == "__main__":
    main()
