"""Opérations sur les observations ('sightings') issues des recherches de personnes."""

from __future__ import annotations

from dogari.storage.database import db_session
from dogari.storage.models import PersonSighting


def create_sighting(
    search_id: str,
    user_id: int | None,
    full_name: str | None,
    camera_source: str | None,
    similarity_score: float | None,
) -> PersonSighting:
    """Journalise une observation d'une personne recherchée sur un flux caméra."""
    with db_session() as connection:
        cursor = connection.execute(
            """
            INSERT INTO person_sightings (search_id, user_id, full_name, camera_source, similarity_score)
            VALUES (?, ?, ?, ?, ?)
            """,
            (search_id, user_id, full_name, camera_source, similarity_score),
        )
        sighting_id = cursor.lastrowid
        row = connection.execute("SELECT * FROM person_sightings WHERE id = ?", (sighting_id,)).fetchone()
    return PersonSighting.from_row(row)


def get_sightings(search_id: str, limit: int = 100) -> list[PersonSighting]:
    """Retourne les observations les plus récentes pour une recherche donnée."""
    with db_session() as connection:
        rows = connection.execute(
            "SELECT * FROM person_sightings WHERE search_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
            (search_id, limit),
        ).fetchall()
    return [PersonSighting.from_row(row) for row in rows]
