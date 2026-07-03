"""Tests des opérations CRUD sur les utilisateurs et les journaux d'accès."""

from __future__ import annotations

import numpy as np
import pytest

from dogari.core.constants import AccessStatus, UserStatus
from dogari.core.exceptions import UserNotFoundError
from dogari.storage import access_logs_repository, users_repository


def test_create_and_get_user(temp_settings):
    user = users_repository.create_user(full_name="Alice Dupont", role="Étudiante")

    fetched = users_repository.get_user_by_id(user.id)

    assert fetched.full_name == "Alice Dupont"
    assert fetched.role == "Étudiante"
    assert fetched.status == UserStatus.ACTIVE.value
    assert fetched.is_active is True


def test_get_user_by_id_raises_when_missing(temp_settings):
    with pytest.raises(UserNotFoundError):
        users_repository.get_user_by_id(999)


def test_get_all_users_filters_inactive(temp_settings):
    active = users_repository.create_user(full_name="Bob")
    inactive = users_repository.create_user(full_name="Charlie")
    users_repository.deactivate_user(inactive.id)

    all_users = users_repository.get_all_users(include_inactive=True)
    active_only = users_repository.get_all_users(include_inactive=False)

    assert {u.id for u in all_users} == {active.id, inactive.id}
    assert {u.id for u in active_only} == {active.id}


def test_get_active_users_with_embeddings(temp_settings):
    embedding = np.random.rand(128)
    with_embedding = users_repository.create_user(full_name="Dana", face_embedding=embedding)
    users_repository.create_user(full_name="Eve")  # sans embedding

    result = users_repository.get_active_users_with_embeddings()

    assert [u.id for u in result] == [with_embedding.id]
    assert np.allclose(result[0].embedding, embedding)


def test_update_user(temp_settings):
    user = users_repository.create_user(full_name="Frank", role="Visiteur")

    updated = users_repository.update_user(user.id, role="Employé")

    assert updated.full_name == "Frank"
    assert updated.role == "Employé"


def test_delete_user(temp_settings):
    user = users_repository.create_user(full_name="Gina")

    users_repository.delete_user(user.id)

    with pytest.raises(UserNotFoundError):
        users_repository.get_user_by_id(user.id)


def test_create_and_query_access_logs(temp_settings):
    user = users_repository.create_user(full_name="Hugo")

    access_logs_repository.create_log(
        status=AccessStatus.GRANTED.value,
        user_id=user.id,
        full_name=user.full_name,
        similarity_score=0.92,
        camera_source="0",
        message="Accès autorisé",
    )
    access_logs_repository.create_log(status=AccessStatus.DENIED.value, message="Visage inconnu")

    recent = access_logs_repository.get_recent_logs(limit=10)
    user_logs = access_logs_repository.get_logs_for_user(user.id)

    assert len(recent) == 2
    assert recent[0].status == AccessStatus.DENIED.value  # dernier créé en premier
    assert len(user_logs) == 1
    assert user_logs[0].full_name == "Hugo"
