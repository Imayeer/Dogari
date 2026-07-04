"""Routes de déclenchement et de consultation du contrôle d'accès."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException

from dogari.access.anomaly import detect_anomalies
from dogari.access.controller import AccessController
from dogari.core.config import settings
from dogari.core.exceptions import DogariError
from dogari.storage.access_logs_repository import get_recent_logs
from dogari.web.schemas import AccessAttemptOut, AccessLogOut, AnomalyEventOut

router = APIRouter(prefix="/api/access", tags=["access"])


@router.post("/recognize", response_model=AccessAttemptOut)
def recognize(camera: Literal["primary", "secondary"] = "primary") -> AccessAttemptOut:
    """Lance une tentative de reconnaissance faciale depuis la caméra choisie (principale ou IP secondaire)."""
    camera_source = None
    if camera == "secondary":
        if settings.secondary_camera_source is None:
            raise HTTPException(
                status_code=400,
                detail="Aucune caméra secondaire configurée (DOGARI_SECONDARY_CAMERA_SOURCE).",
            )
        camera_source = settings.secondary_camera_source

    controller = AccessController(camera_source=camera_source)
    try:
        result = controller.attempt_access()
    except DogariError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return AccessAttemptOut(
        access_status=result.access_status.value,
        recognition_status=result.recognition_status.value,
        user_id=result.user.id if result.user else None,
        full_name=result.user.full_name if result.user else None,
        similarity_score=result.similarity_score,
        message=result.message,
        log_id=result.log.id,
    )


@router.get("/logs", response_model=list[AccessLogOut])
def logs(limit: int = 50) -> list[AccessLogOut]:
    """Retourne les tentatives d'accès les plus récentes."""
    return [AccessLogOut.from_log(log) for log in get_recent_logs(limit=limit)]


@router.get("/anomalies", response_model=list[AnomalyEventOut])
def anomalies() -> list[AnomalyEventOut]:
    """Analyse l'historique des accès et retourne les anomalies détectées."""
    return [AnomalyEventOut.from_event(event) for event in detect_anomalies()]
