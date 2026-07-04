"""Exceptions personnalisées du projet Dogari."""

from __future__ import annotations


class DogariError(Exception):
    """Exception de base pour toutes les erreurs propres à Dogari."""


# --- Vision -----------------------------------------------------------------


class CameraError(DogariError):
    """La caméra ne peut pas être ouverte ou une capture a échoué."""


class NoFaceDetectedError(DogariError):
    """Aucun visage n'a été détecté dans l'image analysée."""


class MultipleFacesDetectedError(DogariError):
    """Plusieurs visages ont été détectés alors qu'un seul était attendu."""


class ModelLoadError(DogariError):
    """Un modèle ONNX (détection YuNet ou reconnaissance SFace) est introuvable ou invalide."""


# --- Storage ------------------------------------------------------------


class DatabaseError(DogariError):
    """Erreur liée à l'accès ou à l'écriture dans la base de données."""


class UserNotFoundError(DogariError):
    """L'utilisateur demandé n'existe pas dans la base de données."""


# --- Access control -----------------------------------------------------


class DoorControlError(DogariError):
    """Erreur lors de la commande d'ouverture/fermeture de la porte."""
