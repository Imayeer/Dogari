"""Recherche continue d'une personne nommée sur un flux caméra.

Démarre une surveillance en arrière-plan (voir `access/camera_watcher.py`) qui
compare chaque visage détecté sur la caméra choisie à l'embedding d'un
utilisateur enregistré nommé, et journalise chaque observation ("sighting")
dans la base de données via `storage/sightings_repository.py`.

Priorité donnée à l'utilisateur explicitement nommé et déjà enregistré dans
le système (consentement implicite de l'enregistrement) : ce n'est pas un
outil de suivi de personnes non enregistrées.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

from dogari.access.camera_watcher import CameraWatcher, new_watcher_id
from dogari.core.config import settings
from dogari.core.exceptions import UserNotFoundError
from dogari.storage.models import User
from dogari.storage.sightings_repository import create_sighting
from dogari.storage.users_repository import get_all_users
from dogari.vision.detector import detect_single_face
from dogari.vision.embeddings import euclidean_distance, generate_embedding, similarity_score


@dataclass
class PersonSearch:
    """État d'une recherche continue d'une personne nommée."""

    search_id: str
    full_name: str
    camera_source: int | str
    watcher: CameraWatcher
    sightings_count: int = 0
    started_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    @property
    def is_running(self) -> bool:
        return self.watcher.is_running

    @property
    def last_error(self) -> str | None:
        return self.watcher.last_error


_active_searches: dict[str, PersonSearch] = {}
_registry_lock = threading.Lock()


def find_target_user(full_name: str) -> User:
    """Trouve un utilisateur actif avec embedding correspondant exactement au nom donné."""
    matches = [
        user
        for user in get_all_users(include_inactive=False)
        if user.full_name == full_name and user.face_embedding is not None
    ]
    if not matches:
        raise UserNotFoundError(
            f"Aucun utilisateur actif avec un visage enregistré trouvé pour '{full_name}'."
        )
    return matches[0]


def check_frame_for_target(frame: np.ndarray, target_embedding: np.ndarray, tolerance: float) -> float | None:
    """Compare le visage détecté dans `frame` à `target_embedding` ; retourne la distance si dans la tolérance."""
    face = detect_single_face(frame)
    if face is None:
        return None
    embedding = generate_embedding(frame, face)
    distance = euclidean_distance(embedding, target_embedding)
    return distance if distance <= tolerance else None


def _make_on_frame(search_id: str, full_name: str, user_id: int, camera_source: int | str, target_embedding: np.ndarray):
    state = {"last_sighting_at": 0.0}

    def on_frame(frame: np.ndarray) -> None:
        distance = check_frame_for_target(frame, target_embedding, settings.recognition_tolerance)
        if distance is None:
            return
        now = time.monotonic()
        if now - state["last_sighting_at"] < settings.search_sighting_cooldown_seconds:
            return
        state["last_sighting_at"] = now
        create_sighting(
            search_id=search_id,
            user_id=user_id,
            full_name=full_name,
            camera_source=str(camera_source),
            similarity_score=similarity_score(distance),
        )
        search = _active_searches.get(search_id)
        if search is not None:
            search.sightings_count += 1

    return on_frame


def start_search(full_name: str, camera_source: int | str) -> PersonSearch:
    """Démarre une surveillance continue pour retrouver un utilisateur nommé sur une caméra."""
    user = find_target_user(full_name)
    search_id = new_watcher_id()
    watcher = CameraWatcher(
        watcher_id=search_id,
        camera_source=camera_source,
        on_frame=_make_on_frame(search_id, full_name, user.id, camera_source, user.embedding),
        poll_interval_seconds=settings.search_poll_interval_seconds,
    )
    search = PersonSearch(
        search_id=search_id, full_name=full_name, camera_source=camera_source, watcher=watcher
    )
    with _registry_lock:
        _active_searches[search_id] = search
    watcher.start()
    return search


def stop_search(search_id: str) -> None:
    """Arrête une recherche continue en cours."""
    with _registry_lock:
        search = _active_searches.get(search_id)
    if search is None:
        raise UserNotFoundError(f"Aucune recherche active avec l'identifiant {search_id!r}.")
    search.watcher.stop()


def get_search(search_id: str) -> PersonSearch:
    """Retourne l'état d'une recherche (active ou arrêtée) par son identifiant."""
    with _registry_lock:
        search = _active_searches.get(search_id)
    if search is None:
        raise UserNotFoundError(f"Aucune recherche avec l'identifiant {search_id!r}.")
    return search


def list_active_searches() -> list[PersonSearch]:
    """Retourne les recherches actuellement en cours d'exécution."""
    with _registry_lock:
        return [search for search in _active_searches.values() if search.is_running]
