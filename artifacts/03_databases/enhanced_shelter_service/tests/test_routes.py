"""Route-level tests with FastAPI's TestClient + mongomock under the hood.

Author: Sanjay Chauhan
Date:   2026-06-07
CS499 Enhancement Three rebuild of the CS340 Austin Animal Center project.

These tests verify the HTTP shape of the API: login + token round-trip,
401 vs 403 vs 200 on protected endpoints, admin-only DELETE, staff
forbidden from DELETE. They do not exercise 2dsphere proximity or
aggregation operators because mongomock cannot run them; the spec tests
in test_specs.py cover the shapes of those, and the docker-compose path
in the README runs them end-to-end against real Mongo.
"""

from __future__ import annotations

import mongomock
import pytest
from fastapi.testclient import TestClient

from app.auth import hash_password
from app.config import settings
from app.db import build_repository
from app.main import create_app
from app.models import Role


@pytest.fixture
def client_with_users():
    """Spin up a TestClient against an in-memory repository."""
    mongo_client = mongomock.MongoClient()
    db = mongo_client[settings.db_name]
    repo = build_repository(
        db,
        animals_collection=settings.animals_collection,
        users_collection=settings.users_collection,
        audit_collection=settings.audit_collection,
    )
    # Seed three users covering each role.
    db[settings.users_collection].insert_many(
        [
            {
                "username": "alice",
                "password_hash": hash_password("AdminPassw0rd!"),
                "role": Role.ADMIN.value,
            },
            {
                "username": "bob",
                "password_hash": hash_password("StaffPassw0rd!"),
                "role": Role.STAFF.value,
            },
            {
                "username": "carol",
                "password_hash": hash_password("ViewerPassw0rd!"),
                "role": Role.VIEWER.value,
            },
        ]
    )

    app = create_app()
    # Attach the mongomock-backed repository directly to app.state and
    # construct TestClient without `with`. The `with` form would trigger
    # the FastAPI lifespan, which builds a real MongoClient against
    # MONGO_URI and would hang in a sandbox that has no Mongo running.
    # We skip the lifespan here on purpose -- the live path is exercised
    # by uvicorn + docker compose, documented in README.
    app.state.repository = repo
    app.state.mongo_client = mongo_client

    tc = TestClient(app)
    try:
        yield tc, repo
    finally:
        mongo_client.close()


def _login(tc: TestClient, username: str, password: str) -> str:
    resp = tc.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _sample_payload(animal_id: str = "A999001") -> dict:
    return {
        "animal_id": animal_id,
        "animal_type": "Dog",
        "breed": "Labrador Retriever Mix",
        "color": "Black",
        "name": "Rex",
        "sex_upon_outcome": "Neutered Male",
        "age_upon_outcome_in_weeks": 80.0,
        "location": {"type": "Point", "coordinates": [-97.74, 30.27]},
    }


def test_login_returns_token(client_with_users):
    tc, _ = client_with_users
    resp = tc.post(
        "/auth/login", json={"username": "alice", "password": "AdminPassw0rd!"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0


def test_login_rejects_bad_password(client_with_users):
    tc, _ = client_with_users
    resp = tc.post(
        "/auth/login", json={"username": "alice", "password": "WrongPassword!"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"] == "invalid credentials"


def test_protected_endpoint_requires_token(client_with_users):
    tc, _ = client_with_users
    resp = tc.get("/animals")
    assert resp.status_code == 401


def test_admin_can_create_and_delete(client_with_users):
    tc, repo = client_with_users
    token = _login(tc, "alice", "AdminPassw0rd!")

    create_resp = tc.post("/animals", json=_sample_payload("A100001"), headers=_auth(token))
    assert create_resp.status_code == 201, create_resp.text

    delete_resp = tc.delete("/animals/A100001", headers=_auth(token))
    assert delete_resp.status_code == 200
    assert delete_resp.json()["deleted"] == 1


def test_staff_can_create_but_not_delete(client_with_users):
    tc, _ = client_with_users
    staff_token = _login(tc, "bob", "StaffPassw0rd!")

    create_resp = tc.post(
        "/animals", json=_sample_payload("A100002"), headers=_auth(staff_token)
    )
    assert create_resp.status_code == 201

    delete_resp = tc.delete("/animals/A100002", headers=_auth(staff_token))
    assert delete_resp.status_code == 403


def test_viewer_cannot_create(client_with_users):
    tc, _ = client_with_users
    viewer_token = _login(tc, "carol", "ViewerPassw0rd!")
    resp = tc.post("/animals", json=_sample_payload("A100003"), headers=_auth(viewer_token))
    assert resp.status_code == 403


def test_viewer_can_list(client_with_users):
    tc, _ = client_with_users
    viewer_token = _login(tc, "carol", "ViewerPassw0rd!")
    resp = tc.get("/animals", headers=_auth(viewer_token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_update_returns_404_for_missing_animal(client_with_users):
    tc, _ = client_with_users
    token = _login(tc, "alice", "AdminPassw0rd!")
    resp = tc.put(
        "/animals/NO-SUCH-ID",
        json={"name": "Ghost"},
        headers=_auth(token),
    )
    assert resp.status_code == 404


def test_register_user_admin_only(client_with_users):
    tc, _ = client_with_users
    admin_token = _login(tc, "alice", "AdminPassw0rd!")
    staff_token = _login(tc, "bob", "StaffPassw0rd!")

    # Staff cannot register a new user.
    forbidden = tc.post(
        "/auth/register",
        json={"username": "newbie", "password": "Password123!", "role": "viewer"},
        headers=_auth(staff_token),
    )
    assert forbidden.status_code == 403

    # Admin can.
    ok = tc.post(
        "/auth/register",
        json={"username": "newbie", "password": "Password123!", "role": "viewer"},
        headers=_auth(admin_token),
    )
    assert ok.status_code == 201
    assert ok.json() == {"username": "newbie", "role": "viewer"}


def test_validation_error_returns_422_with_envelope(client_with_users):
    tc, _ = client_with_users
    token = _login(tc, "alice", "AdminPassw0rd!")

    bad_payload = _sample_payload("A100099")
    bad_payload["location"]["coordinates"] = [200.0, 0.0]  # lon out of range

    resp = tc.post("/animals", json=bad_payload, headers=_auth(token))
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"] == "validation failed"
    assert "details" in body
