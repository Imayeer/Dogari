"""Peuple la base de données avec des valeurs par défaut au premier démarrage.

Convertit l'ancienne configuration par variables d'environnement
(`DOGARI_CAMERA_INDEX`, `DOGARI_SECONDARY_CAMERA_SOURCE`, `DOGARI_USE_GPIO`,
`DOGARI_GPIO_RELAY_PIN`) en un portail et une caméra IP par défaut, uniquement
si la base est vierge (aucun portail existant). Au-delà du premier démarrage,
les portails et caméras IP se gèrent via l'API/le tableau de bord, plus via
ces variables d'environnement.
"""

from __future__ import annotations

from dogari.core.config import settings
from dogari.storage.ip_cameras_repository import create_ip_camera, get_all_ip_cameras
from dogari.storage.portals_repository import create_portal, get_all_portals


def seed_defaults() -> None:
    """Crée un portail et une caméra IP par défaut si la base ne contient encore rien."""
    if not get_all_portals():
        camera_kind = "usb" if isinstance(settings.camera_source, int) else "ip"
        create_portal(
            name="Portail principal",
            camera_source=str(settings.camera_source),
            camera_kind=camera_kind,
            door_type="gpio" if settings.use_gpio else "simulated",
            gpio_relay_pin=settings.gpio_relay_pin if settings.use_gpio else None,
        )

    if settings.secondary_camera_source is not None and not get_all_ip_cameras():
        create_ip_camera(name="Caméra secondaire", source=str(settings.secondary_camera_source))
