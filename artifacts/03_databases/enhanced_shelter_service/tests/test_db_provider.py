"""Unit tests for the role-scoped MongoDB client factory (M7).

Author: Sanjay Chauhan
Date:   2026-06-20
CS499 Enhancement Three (Module 7 hardening) for the CS340 Austin Animal
Center project.

These tests cover the DB-tier isolation selection logic WITHOUT a live Mongo:

  - resolve_uri_for_role falls back to the service-account URI when a role
    URI is blank (the conftest config sets no per-role URIs, so this is the
    real default the grader sees).
  - ClientFactory creates ONE pool per distinct URI (one in fallback mode,
    three when fully isolated) and returns a working Repository per role.

settings is a frozen dataclass, so rather than monkeypatch it we inject a
custom uri_resolver and client_maker. The factory's job is selection and
pooling -- pure bookkeeping -- so no real socket is opened.
"""

from __future__ import annotations

import mongomock

from app.config import settings
from app.db_provider import ClientFactory, resolve_uri_for_role
from app.models import Role


def test_resolve_uri_falls_back_to_service_account():
    # conftest sets MONGO_URI but no per-role URIs, so every role must
    # resolve to the single service account. This is the grader's default.
    assert settings.mongo_uri_admin == ""
    assert settings.mongo_uri_staff == ""
    assert settings.mongo_uri_viewer == ""
    for role in (Role.ADMIN, Role.STAFF, Role.VIEWER):
        assert resolve_uri_for_role(role) == settings.mongo_uri


def test_factory_fallback_mode_shares_one_pool():
    """All roles resolve to the same URI -> exactly one pool is created."""
    made = []

    def maker(uri):
        made.append(uri)
        return mongomock.MongoClient()

    # uri_resolver returns the same URI for every role == fallback mode.
    fallback_resolver = lambda role: settings.mongo_uri  # noqa: E731
    factory = ClientFactory(
        client_maker=maker, uri_resolver=fallback_resolver, isolated_mode=False
    )
    assert factory.isolated_mode is False

    factory.repository_for_role(Role.ADMIN)
    factory.repository_for_role(Role.STAFF)
    factory.repository_for_role(Role.VIEWER)

    assert factory.pool_count() == 1
    assert made == [settings.mongo_uri]

    factory.close()
    assert factory.pool_count() == 0


def test_factory_isolated_mode_creates_distinct_pools():
    """Three distinct role URIs -> three distinct connection pools."""
    role_uris = {
        Role.ADMIN: "mongodb://aac_admin@h/aac",
        Role.STAFF: "mongodb://aac_staff@h/aac",
        Role.VIEWER: "mongodb://aac_viewer@h/aac",
    }
    factory = ClientFactory(
        client_maker=lambda uri: mongomock.MongoClient(),
        uri_resolver=lambda role: role_uris[role],
        isolated_mode=True,
    )
    assert factory.isolated_mode is True

    factory.repository_for_role(Role.ADMIN)
    factory.repository_for_role(Role.STAFF)
    factory.repository_for_role(Role.VIEWER)

    assert factory.pool_count() == 3
    factory.close()


def test_factory_reuses_pool_for_same_role():
    """Calling twice for the same role must NOT spin up a second pool."""
    factory = ClientFactory(
        client_maker=lambda uri: mongomock.MongoClient(),
        uri_resolver=lambda role: settings.mongo_uri,
        isolated_mode=False,
    )
    factory.repository_for_role(Role.STAFF)
    factory.repository_for_role(Role.STAFF)
    assert factory.pool_count() == 1
    factory.close()


def test_factory_returns_usable_repository():
    factory = ClientFactory(
        client_maker=lambda uri: mongomock.MongoClient(),
        uri_resolver=lambda role: settings.mongo_uri,
        isolated_mode=False,
    )
    repo = factory.repository_for_role(Role.STAFF)
    assert repo.animals.name == settings.animals_collection
    assert repo.find_user("nobody") is None
    factory.close()
