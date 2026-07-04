"""Route de génération de rapports de synthèse sur l'historique des accès."""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from dogari.access.reports import generate_report_for_last_days, render_report_csv, render_report_text
from dogari.web.schemas import AccessReportOut

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/summary", response_model=AccessReportOut)
def summary(days: int = Query(7, ge=1, le=365)) -> AccessReportOut:
    """Retourne un rapport de synthèse des accès sur les `days` derniers jours."""
    return AccessReportOut.from_report(generate_report_for_last_days(days))


@router.get("/export.csv", response_class=PlainTextResponse)
def export_csv(days: int = Query(7, ge=1, le=365)) -> PlainTextResponse:
    """Exporte la répartition quotidienne du rapport au format CSV téléchargeable."""
    report = generate_report_for_last_days(days)
    return PlainTextResponse(
        content=render_report_csv(report),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=dogari_rapport_{days}j.csv"},
    )


@router.get("/export.txt", response_class=PlainTextResponse)
def export_text(days: int = Query(7, ge=1, le=365)) -> PlainTextResponse:
    """Exporte le rapport complet au format texte téléchargeable."""
    report = generate_report_for_last_days(days)
    return PlainTextResponse(
        content=render_report_text(report),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=dogari_rapport_{days}j.txt"},
    )
