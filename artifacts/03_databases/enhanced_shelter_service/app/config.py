"""Configuration loader.

Author: Sanjay Chauhan
Date:   2026-06-07
CS499 Enhancement Three rebuild of the CS340 Austin Animal Center project.

This module reads required environment variables from `.env` (when present)
and refuses to import if any required value is missing. The original CS340
notebook hardcoded `username = "aacuser"` / `password = "***"` directly
in the source -- fail-fast at import time is the deliberate opposite of that
pattern. If a deployment is missing a secret, we want a loud crash on boot,
not a silent fall-back to a known-bad default.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Final

from dotenv import load_dotenv

# Load .env from the current working directory if present. We do this at
# import time so any module that imports `settings` sees a populated env.
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    """Immutable application settings.

    Frozen so a route handler cannot accidentally mutate config at runtime.
    """

    mongo_uri: str
    jwt_secret: str
    # ---------------------------------------------------------------------
    # Per-role Mongo connection URIs (M7 DB-tier isolation, OPTIONAL).
    # ---------------------------------------------------------------------
    # When set, the app connects to MongoDB using a credential whose
    # Mongo-side privileges match the caller's JWT role (admin/staff/viewer),
    # so a viewer-scoped request physically cannot insert/update/remove at
    # the database tier even if a bug let it past the JWT require_role check.
    # When LEFT BLANK, the app falls back to the single `mongo_uri` service
    # account for every role -- this keeps the project runnable for a grader
    # who has not provisioned three Mongo users. The fallback is intentional
    # and documented; it does NOT weaken the JWT-layer enforcement, which is
    # always active. See app/db_provider.py for the selection logic.
    mongo_uri_admin: str = ""
    mongo_uri_staff: str = ""
    mongo_uri_viewer: str = ""
    jwt_algorithm: str = "HS256"
    # 8-hour TTL matches the architecture plan. Short enough that a leaked
    # token expires the same workday, long enough that staff are not retyping
    # passwords between morning and afternoon intake.
    jwt_ttl_seconds: int = 8 * 60 * 60
    bcrypt_rounds: int = 12
    db_name: str = "aac"
    animals_collection: str = "animals_geo"
    audit_collection: str = "audit_log"
    users_collection: str = "users"


def _require(name: str) -> str:
    """Return os.environ[name] or raise RuntimeError with a clear message.

    Why RuntimeError on import: the FastAPI app, every helper script, and
    every test imports this module. A missing secret should fail the entire
    process before a single route is registered, never silently default.
    """
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Required environment variable {name!r} is not set. "
            f"Copy .env.example to .env and fill in real values."
        )
    return value


# Resolved at import time. If MONGO_URI or JWT_SECRET is missing, importing
# any module in this package raises RuntimeError immediately.
settings: Final[Settings] = Settings(
    mongo_uri=_require("MONGO_URI"),
    jwt_secret=_require("JWT_SECRET"),
    # Optional per-role URIs. Absent -> "" -> fall back to mongo_uri. We use
    # os.environ.get (not _require) precisely because these are optional; a
    # grader without three Mongo users still gets a working app.
    mongo_uri_admin=os.environ.get("MONGO_URI_ADMIN", ""),
    mongo_uri_staff=os.environ.get("MONGO_URI_STAFF", ""),
    mongo_uri_viewer=os.environ.get("MONGO_URI_VIEWER", ""),
)
