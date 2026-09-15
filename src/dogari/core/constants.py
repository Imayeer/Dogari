"""Constantes partagées par l'ensemble des modules Dogari."""

from __future__ import annotations

from enum import Enum


class AccessStatus(str, Enum):
    """Statut d'une tentative d'accès."""

    GRANTED = "granted"
    DENIED = "denied"
    ERROR = "error"


class UserStatus(str, Enum):
    """Statut d'un utilisateur enregistré."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class RecognitionStatus(str, Enum):
    """Résultat d'une opération de reconnaissance faciale."""

    AUTHORIZED = "authorized"
    UNKNOWN = "unknown"
    NO_FACE_DETECTED = "no_face_detected"
    MULTIPLE_FACES_DETECTED = "multiple_faces_detected"
    SPOOF_DETECTED = "spoof_detected"
    PORTAL_NOT_AUTHORIZED = "portal_not_authorized"
    ERROR = "error"


DEFAULT_CAMERA_SOURCE_LABEL = "default"
FACE_IMAGE_EXTENSION = ".jpg"
