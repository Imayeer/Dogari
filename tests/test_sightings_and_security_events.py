"""Tests des opérations CRUD sur les observations et événements de sécurité."""

from __future__ import annotations

from dogari.storage import security_events_repository, sightings_repository
from dogari.storage.users_repository import create_user


def test_create_and_get_sightings(temp_settings):
    user = create_user(full_name="Nora")

    sightings_repository.create_sighting(
        search_id="search-1", user_id=user.id, full_name="Nora", camera_source="1", similarity_score=0.8
    )
    sightings_repository.create_sighting(
        search_id="search-1", user_id=user.id, full_name="Nora", camera_source="1", similarity_score=0.9
    )
    sightings_repository.create_sighting(
        search_id="search-2", user_id=user.id, full_name="Nora", camera_source="1", similarity_score=0.7
    )

    results = sightings_repository.get_sightings("search-1")

    assert len(results) == 2
    assert all(s.search_id == "search-1" for s in results)


def test_create_and_get_security_events(temp_settings):
    security_events_repository.create_security_event(
        kind="crowd_detected", severity="warning", message="5 personnes détectées", camera_source="1"
    )
    security_events_repository.create_security_event(
        kind="weapon_detected", severity="critical", message="knife (0.75)", camera_source="1"
    )

    events = security_events_repository.get_recent_security_events()

    assert len(events) == 2
    assert events[0].kind == "weapon_detected"  # le plus récent en premier
