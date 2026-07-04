"""Vérification des droits d'accès d'un rôle à un portail, selon un planning hebdomadaire.

Un rôle n'a accès à un portail qu'aux jours de semaine et créneaux horaires
explicitement configurés (`role_portal_schedules`) : aucune plage définie pour
un portail donné signifie aucun accès à ce portail, à aucun moment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time as dt_time

from dogari.storage.role_schedules_repository import get_schedules_for_role_and_portal


@dataclass
class RoleAccessResult:
    """Résultat de la vérification d'accès d'un rôle à un portail."""

    authorized: bool
    reason: str


def is_role_authorized_for_portal(
    role_id: int | None, portal_id: int, now: datetime | None = None
) -> RoleAccessResult:
    """Vérifie si un rôle a accès à un portail au moment donné (jour de semaine + heure)."""
    if role_id is None:
        return RoleAccessResult(authorized=False, reason="Aucun rôle d'accès associé à cet utilisateur.")

    now = now or datetime.now()
    weekday = now.weekday()  # 0 = lundi ... 6 = dimanche
    current_time = now.time()

    schedules = get_schedules_for_role_and_portal(role_id, portal_id)
    if not schedules:
        return RoleAccessResult(authorized=False, reason="Ce rôle n'a accès à aucun horaire pour ce portail.")

    for schedule in schedules:
        if schedule.weekday != weekday:
            continue
        start = dt_time.fromisoformat(schedule.start_time)
        end = dt_time.fromisoformat(schedule.end_time)
        if start <= current_time <= end:
            return RoleAccessResult(authorized=True, reason="Accès autorisé.")

    return RoleAccessResult(
        authorized=False, reason="Ce rôle n'a pas accès à ce portail à ce jour/heure."
    )
