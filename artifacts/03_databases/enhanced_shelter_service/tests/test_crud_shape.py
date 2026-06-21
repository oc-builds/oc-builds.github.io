"""CRUD shape tests against mongomock.

Author: Sanjay Chauhan
Date:   2026-06-07
CS499 Enhancement Three rebuild of the CS340 Austin Animal Center project.

These tests verify CRUD SHAPE only -- the chokepoint writes through to the
operational collection AND the audit_log collection in the same call, the
Pydantic models reject invalid coordinates, password length is enforced,
and JWT round-trips work. They do NOT verify $jsonSchema enforcement,
2dsphere proximity, or aggregation operators (mongomock does not implement
those features). The pure-spec assertions for those live in test_specs.py.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app import crud
from app.auth import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.config import settings
from app.models import (
    AnimalCreate,
    AnimalUpdate,
    GeoPoint,
    LoginRequest,
    Role,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_animal(animal_id: str = "A123456") -> AnimalCreate:
    return AnimalCreate(
        animal_id=animal_id,
        animal_type="Dog",
        breed="Labrador Retriever Mix",
        color="Black",
        name="Fido",
        sex_upon_outcome="Neutered Male",
        age_upon_outcome_in_weeks=78.0,
        location=GeoPoint(type="Point", coordinates=[-97.74, 30.27]),
    )


# ---------------------------------------------------------------------------
# Chokepoint: create / read / update / delete + audit
# ---------------------------------------------------------------------------


def test_create_writes_animal_and_audit(repo):
    payload = _sample_animal()
    result = crud.create_animal(
        repo,
        payload,
        user="testuser",
        collection_name=settings.animals_collection,
    )
    assert result["audited"] is True
    assert "inserted_id" in result

    # The animal exists in the operational collection.
    doc = repo.find_one_animal({"animal_id": payload.animal_id})
    assert doc is not None
    assert doc["breed"] == "Labrador Retriever Mix"

    # An audit entry exists with action=create_animal.
    audits = list(repo._audit._col.find({}))
    assert len(audits) == 1
    assert audits[0]["action"] == "create_animal"
    assert audits[0]["user"] == "testuser"
    assert audits[0]["after"]["animal_id"] == payload.animal_id


def test_update_writes_audit_with_before_and_after(repo):
    payload = _sample_animal()
    crud.create_animal(
        repo, payload, user="u", collection_name=settings.animals_collection
    )
    crud.update_animal(
        repo,
        payload.animal_id,
        AnimalUpdate(name="Buddy"),
        user="u",
        collection_name=settings.animals_collection,
    )
    audits = list(repo._audit._col.find({"action": "update_animal"}))
    assert len(audits) == 1
    assert audits[0]["before"]["name"] == "Fido"
    assert audits[0]["after"]["name"] == "Buddy"


def test_delete_writes_audit_with_before(repo):
    payload = _sample_animal()
    crud.create_animal(
        repo, payload, user="u", collection_name=settings.animals_collection
    )
    result = crud.delete_animal(
        repo,
        payload.animal_id,
        user="u",
        collection_name=settings.animals_collection,
    )
    assert result["deleted"] == 1
    audits = list(repo._audit._col.find({"action": "delete_animal"}))
    assert len(audits) == 1
    assert audits[0]["before"]["animal_id"] == payload.animal_id


def test_direct_write_does_not_produce_audit_entry(repo):
    """The chokepoint is what creates audit entries. A direct collection
    write bypasses it and MUST NOT produce one. This is the negative test
    that proves the property the architecture plan claims.
    """
    repo.animals.insert_one(
        {
            "animal_id": "DIRECT-WRITE",
            "animal_type": "Dog",
            "breed": "X",
            "location": {"type": "Point", "coordinates": [0.0, 0.0]},
        }
    )
    assert repo._audit._col.count_documents({}) == 0


def test_audit_redacts_password_and_token_fields(repo):
    """A user-creation write should NOT leave the password in the audit."""
    repo.save_with_audit(
        user="admin",
        action="register_user",
        collection_name=settings.users_collection,
        target_id="alice",
        operation="insert",
        payload={
            "username": "alice",
            "password_hash": "should-be-redacted",
            "token": "should-also-be-redacted",
            "role": "viewer",
        },
    )
    audit = repo._audit._col.find_one({"action": "register_user"})
    assert audit is not None
    after = audit["after"]
    assert "password_hash" not in after
    assert "token" not in after
    assert after["username"] == "alice"
    assert after["role"] == "viewer"


# ---------------------------------------------------------------------------
# Pydantic validation
# ---------------------------------------------------------------------------


def test_geopoint_rejects_out_of_range_longitude():
    with pytest.raises(ValidationError):
        GeoPoint(type="Point", coordinates=[200.0, 0.0])


def test_geopoint_rejects_out_of_range_latitude():
    with pytest.raises(ValidationError):
        GeoPoint(type="Point", coordinates=[0.0, 95.0])


def test_geopoint_accepts_boundary_values():
    GeoPoint(type="Point", coordinates=[-180.0, -90.0])
    GeoPoint(type="Point", coordinates=[180.0, 90.0])


def test_loginrequest_rejects_short_password():
    with pytest.raises(ValidationError):
        LoginRequest(username="x", password="short")


def test_loginrequest_accepts_valid_password():
    LoginRequest(username="x", password="long-enough-pw")


# ---------------------------------------------------------------------------
# Auth round-trip
# ---------------------------------------------------------------------------


def test_bcrypt_roundtrip():
    h = hash_password("Password123!")
    assert verify_password("Password123!", h) is True
    assert verify_password("wrong", h) is False


def test_jwt_roundtrip():
    token, ttl = create_access_token(subject="bob", role=Role.STAFF)
    assert ttl == settings.jwt_ttl_seconds
    claims = decode_token(token)
    assert claims["sub"] == "bob"
    assert claims["role"] == "staff"


def test_jwt_decode_rejects_garbage():
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        decode_token("not-a-real-token")
