"""Routes de gestion des utilisateurs autorisés."""

from __future__ import annotations

import re
import time

import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from dogari.core.config import settings
from dogari.core.constants import FACE_IMAGE_EXTENSION
from dogari.core.exceptions import UserNotFoundError
from dogari.storage.users_repository import (
    create_user,
    delete_user,
    deactivate_user,
    get_all_users,
)
from dogari.vision.detector import detect_single_face
from dogari.vision.embeddings import generate_embedding
from dogari.web.schemas import UserOut

router = APIRouter(prefix="/api/users", tags=["users"])


def _decode_image(contents: bytes) -> np.ndarray:
    import cv2  # import différé : dépendance lourde optionnelle

    array = np.frombuffer(contents, dtype=np.uint8)
    frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="Fichier image invalide.")
    return frame


def _slugify(full_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", full_name.lower()).strip("-")
    return slug or "user"


@router.get("", response_model=list[UserOut])
def list_users() -> list[UserOut]:
    """Liste tous les utilisateurs enregistrés (actifs et inactifs)."""
    return [UserOut.from_user(user) for user in get_all_users()]


@router.post("", response_model=UserOut, status_code=201)
async def add_user(
    full_name: str = Form(...),
    role: str | None = Form(None),
    face_image: UploadFile = File(...),
) -> UserOut:
    """Ajoute un utilisateur autorisé à partir d'une image de référence."""
    contents = await face_image.read()
    frame = _decode_image(contents)

    face_location = detect_single_face(frame)
    if face_location is None:
        raise HTTPException(status_code=400, detail="Aucun visage détecté dans l'image fournie.")

    embedding = generate_embedding(frame, face_location)

    settings.ensure_directories()
    image_path = settings.faces_dir / f"{_slugify(full_name)}-{int(time.time())}{FACE_IMAGE_EXTENSION}"
    from dogari.vision.camera import save_frame

    save_frame(frame, str(image_path))

    user = create_user(
        full_name=full_name,
        role=role,
        face_image_path=str(image_path),
        face_embedding=embedding,
    )
    return UserOut.from_user(user)


@router.patch("/{user_id}/deactivate", response_model=UserOut)
def deactivate(user_id: int) -> UserOut:
    """Désactive un utilisateur sans supprimer son historique."""
    try:
        user = deactivate_user(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return UserOut.from_user(user)


@router.delete("/{user_id}", status_code=204)
def remove_user(user_id: int) -> None:
    """Supprime définitivement un utilisateur."""
    try:
        delete_user(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
