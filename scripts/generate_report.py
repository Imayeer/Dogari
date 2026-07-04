"""Génère un rapport périodique de synthèse des accès (console, fichier, tâche planifiée).

Usage :
    python scripts/generate_report.py                     # 7 derniers jours, affiché dans la console
    python scripts/generate_report.py --days 30
    python scripts/generate_report.py --days 7 --output rapport.txt
    python scripts/generate_report.py --days 7 --csv rapport.csv

Pour un rapport vraiment "automatique", planifiez ce script via cron, par
exemple chaque lundi à 8h pour un résumé hebdomadaire :

    0 8 * * 1 cd /chemin/vers/dogari && .venv/bin/python scripts/generate_report.py --days 7 --output data/logs/rapport_hebdo.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Permet d'exécuter ce script directement sans installation préalable du paquet.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dogari.access.reports import generate_report_for_last_days, render_report_csv, render_report_text


def main() -> None:
    parser = argparse.ArgumentParser(description="Génère un rapport de synthèse des accès Dogari.")
    parser.add_argument("--days", type=int, default=7, help="Nombre de jours à couvrir (défaut : 7)")
    parser.add_argument("--output", type=Path, default=None, help="Fichier de sortie texte (défaut : console)")
    parser.add_argument("--csv", type=Path, default=None, help="Exporte aussi la répartition quotidienne en CSV")
    args = parser.parse_args()

    report = generate_report_for_last_days(args.days)
    text = render_report_text(report)

    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"Rapport écrit dans {args.output}")
    else:
        print(text)

    if args.csv:
        args.csv.write_text(render_report_csv(report), encoding="utf-8")
        print(f"Répartition quotidienne exportée vers {args.csv}")


if __name__ == "__main__":
    main()
