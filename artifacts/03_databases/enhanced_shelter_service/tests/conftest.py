"""Shared pytest fixtures.

Author: Sanjay Chauhan
Date:   2026-06-07
CS499 Enhancement Three rebuild of the CS340 Austin Animal Center project.

config.py fails fast if MONGO_URI or JWT_SECRET is missing. Tests need
those set BEFORE any `from app...` import. We do that here at module-load
time so individual test files can simply `from app...` and Just Work.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Set required env vars before any app import.
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017/aac_test")
os.environ.setdefault(
    "JWT_SECRET",
    "test-secret-do-not-use-in-prod-this-is-just-a-fixture",
)

# Make the project root importable.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mongomock  # noqa: E402
import pytest  # noqa: E402

from app.config import settings  # noqa: E402
from app.db import build_repository  # noqa: E402


@pytest.fixture
def mongo_db():
    """A fresh mongomock database per test."""
    client = mongomock.MongoClient()
    db = client[settings.db_name]
    yield db
    client.close()


@pytest.fixture
def repo(mongo_db):
    return build_repository(
        mongo_db,
        animals_collection=settings.animals_collection,
        users_collection=settings.users_collection,
        audit_collection=settings.audit_collection,
    )
