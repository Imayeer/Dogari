"""Abstraction du contrôle de la porte (gâche électrique).

Le MVP simule l'ouverture de la porte (affichage/log). Le contrôle GPIO réel
sur Raspberry Pi 5 sera activé en Phase 7 via `GPIODoorController`, sans
changer le reste du code métier (voir `access/controller.py`).
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod

from dogari.core.config import settings
from dogari.core.exceptions import DoorControlError

logger = logging.getLogger("dogari.access.door")


class DoorController(ABC):
    """Interface commune à toutes les implémentations de contrôle de porte."""

    @abstractmethod
    def open_door(self, hold_seconds: float | None = None) -> None:
        """Ouvre la porte puis la referme automatiquement après `hold_seconds`."""

    @abstractmethod
    def close_door(self) -> None:
        """Force la fermeture immédiate de la porte."""


class SimulatedDoorController(DoorController):
    """Simule l'ouverture d'une porte, utilisé pour le développement sur PC."""

    def __init__(self) -> None:
        self.is_open = False

    def open_door(self, hold_seconds: float | None = None) -> None:
        hold = hold_seconds if hold_seconds is not None else settings.door_hold_seconds
        self.is_open = True
        logger.info("[SIMULATION] Porte ouverte pendant %.1fs", hold)
        self.is_open = False

    def close_door(self) -> None:
        self.is_open = False
        logger.info("[SIMULATION] Porte fermée")


class GPIODoorController(DoorController):
    """Contrôle une gâche électrique 12V via un relais piloté par GPIO (Raspberry Pi 5).

    Nécessite la bibliothèque `RPi.GPIO` (ou `gpiozero`), disponible uniquement
    sur Raspberry Pi. L'import est différé pour ne pas casser le MVP sur PC.
    """

    def __init__(self, relay_pin: int | None = None) -> None:
        self.relay_pin = relay_pin if relay_pin is not None else settings.gpio_relay_pin
        try:
            import RPi.GPIO as GPIO  # type: ignore[import-not-found]
        except ImportError as exc:
            raise DoorControlError(
                "RPi.GPIO n'est pas disponible. GPIODoorController ne peut être utilisé "
                "que sur un Raspberry Pi avec la dépendance installée."
            ) from exc

        self._gpio = GPIO
        self._gpio.setmode(GPIO.BCM)
        self._gpio.setup(self.relay_pin, GPIO.OUT, initial=GPIO.LOW)

    def open_door(self, hold_seconds: float | None = None) -> None:
        hold = hold_seconds if hold_seconds is not None else settings.door_hold_seconds
        try:
            self._gpio.output(self.relay_pin, self._gpio.HIGH)
            time.sleep(hold)
        finally:
            self._gpio.output(self.relay_pin, self._gpio.LOW)

    def close_door(self) -> None:
        self._gpio.output(self.relay_pin, self._gpio.LOW)


def get_door_controller() -> DoorController:
    """Retourne l'implémentation de contrôle de porte adaptée à la configuration globale.

    Conservée pour compatibilité (valeurs par défaut/scripts) ; le contrôle
    d'accès réel utilise `get_door_controller_for_portal`, propre à chaque
    portail (voir `access/controller.py`).
    """
    if settings.use_gpio:
        return GPIODoorController()
    return SimulatedDoorController()


def get_door_controller_for_portal(door_type: str, gpio_relay_pin: int | None) -> DoorController:
    """Retourne le contrôleur de porte adapté à la configuration d'un portail donné."""
    if door_type == "gpio":
        return GPIODoorController(relay_pin=gpio_relay_pin)
    return SimulatedDoorController()
