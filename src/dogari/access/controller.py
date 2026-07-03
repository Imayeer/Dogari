"""Orchestration du contrôle d'accès : reconnaissance, décision, porte, journal."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from dogari.core.constants import AccessStatus, RecognitionStatus
from dogari.core.exceptions import CameraError
from dogari.storage.access_logs_repository import create_log
from dogari.storage.models import AccessLog, User
from dogari.storage.users_repository import get_active_users_with_embeddings
from dogari.vision.camera import Camera
from dogari.vision.detector import detect_single_face
from dogari.vision.embeddings import generate_embedding
from dogari.vision.recognizer import FaceRecognizer

from dogari.access.door import DoorController, get_door_controller


@dataclass
class AccessAttemptResult:
    """Résultat complet d'une tentative d'accès, prêt à être exposé par l'API."""

    access_status: AccessStatus
    recognition_status: RecognitionStatus
    user: User | None
    similarity_score: float | None
    message: str
    log: AccessLog


class AccessController:
    """Point d'entrée unique pour lancer une tentative de reconnaissance/accès.

    Les dépendances (caméra, porte) sont injectables afin de permettre les
    tests unitaires sans matériel réel.
    """

    def __init__(
        self,
        door_controller: DoorController | None = None,
        camera_source: int | str | None = None,
    ) -> None:
        self.door_controller = door_controller or get_door_controller()
        self.camera_source = camera_source

    def attempt_access(self, frame: np.ndarray | None = None) -> AccessAttemptResult:
        """Exécute une tentative d'accès complète et journalise le résultat.

        Si `frame` est fourni, la capture caméra est court-circuitée (utile
        pour les tests et pour l'upload d'image via l'API web).
        """
        camera_label = str(self.camera_source) if self.camera_source is not None else "default"

        try:
            if frame is None:
                with Camera(self.camera_source) as camera:
                    frame = camera.capture_frame()
        except CameraError as exc:
            return self._record(
                access_status=AccessStatus.ERROR,
                recognition_status=RecognitionStatus.ERROR,
                user=None,
                similarity_score=None,
                message=str(exc),
                camera_source=camera_label,
            )

        face_location = detect_single_face(frame)
        if face_location is None:
            return self._record(
                access_status=AccessStatus.DENIED,
                recognition_status=RecognitionStatus.NO_FACE_DETECTED,
                user=None,
                similarity_score=None,
                message="Aucun visage détecté dans l'image capturée.",
                camera_source=camera_label,
            )

        embedding = generate_embedding(frame, face_location)
        known_users = get_active_users_with_embeddings()
        recognizer = FaceRecognizer(known_users)
        match = recognizer.identify(embedding)

        if match.matched:
            self.door_controller.open_door()
            return self._record(
                access_status=AccessStatus.GRANTED,
                recognition_status=RecognitionStatus.AUTHORIZED,
                user=match.user,
                similarity_score=match.score,
                message=f"Accès autorisé pour {match.user.full_name}.",
                camera_source=camera_label,
            )

        return self._record(
            access_status=AccessStatus.DENIED,
            recognition_status=RecognitionStatus.UNKNOWN,
            user=None,
            similarity_score=match.score,
            message="Visage détecté mais non reconnu parmi les utilisateurs autorisés.",
            camera_source=camera_label,
        )

    @staticmethod
    def _record(
        access_status: AccessStatus,
        recognition_status: RecognitionStatus,
        user: User | None,
        similarity_score: float | None,
        message: str,
        camera_source: str,
    ) -> AccessAttemptResult:
        log = create_log(
            status=access_status.value,
            user_id=user.id if user else None,
            full_name=user.full_name if user else None,
            similarity_score=similarity_score,
            camera_source=camera_source,
            message=message,
        )
        return AccessAttemptResult(
            access_status=access_status,
            recognition_status=recognition_status,
            user=user,
            similarity_score=similarity_score,
            message=message,
            log=log,
        )
