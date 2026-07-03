"""Routes de déclenchement et de consultation du contrôle d'accès."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from dogari.access.controller import AccessController
from dogari.core.exceptions import DogariError
from dogari.storage.access_logs_repository import get_recent_logs
from dogari.web.schemas import AccessAttemptOut, AccessLogOut

router = APIRouter(prefix="/api/access", tags=["access"])


@router.post("/recognize", response_model=AccessAttemptOut)
def recognize() -> AccessAttemptOut:
    """Lance une tentative de reconnaissance faciale depuis la caméra configurée."""
    controller = AccessController()
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
