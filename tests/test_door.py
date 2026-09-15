"""Tests du contrôleur de porte simulé."""

from __future__ import annotations

from dogari.access.door import SimulatedDoorController


def test_simulated_door_opens_and_closes():
    door = SimulatedDoorController()

    door.open_door(hold_seconds=0)

    assert door.is_open is False  # la porte se referme automatiquement après l'ouverture


def test_simulated_door_close_is_idempotent():
    door = SimulatedDoorController()
    door.close_door()

    assert door.is_open is False
