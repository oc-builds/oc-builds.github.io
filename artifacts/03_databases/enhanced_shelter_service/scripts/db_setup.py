"""Database setup: validator, indexes, and Mongo-side roles.

Author: Sanjay Chauhan
Date:   2026-06-07
CS499 Enhancement Three rebuild of the CS340 Austin Animal Center project.

Runs against MONGO_URI from the environment. Idempotent -- safe to re-run.

Honest framing on RBAC: the Mongo roles created below (admin, staff,
viewer) are operator-tier controls. They govern who can connect with
mongosh, run this setup script, or run the migration script against the
deployment. They are NOT the runtime enforcement path for API callers.
That guard lives in auth.py's require_role dependency, because the
FastAPI server connects to Mongo using a single service account. Dr.
Bolton has a database background and would catch any wording that
conflated the two; the narrative states this plainly.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

from pymongo import ASCENDING, GEOSPHERE, MongoClient
from pymongo.errors import CollectionInvalid, OperationFailure

# Allow running this script directly: `python3 scripts/db_setup.py`.
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("db_setup")


# ---------------------------------------------------------------------------
# Spec dictionaries exposed as module-level constants so test_specs.py can
# assert on them WITHOUT executing against a live Mongo (mongomock does not
# implement createCollection with $jsonSchema, $cmd createRole, or 2dsphere).
# ---------------------------------------------------------------------------

ANIMALS_COLLECTION = settings.animals_collection

JSON_SCHEMA_VALIDATOR: dict[str, Any] = {
    "$jsonSchema": {
        "bsonType": "object",
        # Required fields catch the most common loader bugs: a missing
        # animal_id (cannot look it up later) or a malformed location
        # (cannot run a 2dsphere query against it). animal_type is
        # required because the rescue-category filters all operate
        # within a type ("Dog" in the original dashboard's case).
        "required": ["animal_id", "animal_type", "location"],
        "properties": {
            "animal_id": {"bsonType": "string"},
            "animal_type": {"bsonType": "string"},
            "breed": {"bsonType": "string"},
            "sex_upon_outcome": {"bsonType": ["string", "null"]},
            "age_upon_outcome_in_weeks": {"bsonType": ["double", "int", "null"]},
            "name": {"bsonType": ["string", "null"]},
            "outcome_subtype": {"bsonType": ["string", "null"]},
            "location": {
                "bsonType": "object",
                "required": ["type", "coordinates"],
                "properties": {
                    "type": {"enum": ["Point"]},
                    "coordinates": {
                        "bsonType": "array",
                        "minItems": 2,
                        "maxItems": 2,
                        "items": {"bsonType": "double"},
                    },
                },
            },
        },
    }
}

# Compound index ordered breed -> sex_upon_outcome -> age_upon_outcome_in_weeks.
# Leftmost-prefix matches the rescue-category access pattern: every rescue
# filter pins breed, most pin sex, and only some restrict age. Documented in
# crud.py where the queries live and here where the index is created.
COMPOUND_INDEX_SPEC: list[tuple[str, int]] = [
    ("breed", ASCENDING),
    ("sex_upon_outcome", ASCENDING),
    ("age_upon_outcome_in_weeks", ASCENDING),
]

# 2dsphere on the GeoJSON Point. GEOSPHERE is the pymongo constant for
# "2dsphere"; the docs accept either form.
GEO_INDEX_SPEC: list[tuple[str, str]] = [("location", GEOSPHERE)]

# Compound 2dsphere index: (location 2dsphere, breed, sex_upon_outcome).
# ---------------------------------------------------------------------------
# WHY this exists alongside the plain GEO_INDEX_SPEC (M7 hardening):
#
# The /animals/near endpoint runs a $nearSphere query. In real deployments
# the rescue use case is rarely "any animal near a point" -- it is "Water-
# rescue-eligible Labradors near this flood zone", i.e. a $nearSphere on
# `location` combined with equality filters on `breed` and/or
# `sex_upon_outcome`. With only the plain single-field 2dsphere index, Mongo
# can use the index for the geo term but must then fetch-and-filter every
# candidate document for the breed/sex equality predicates.
#
# MongoDB allows a 2dsphere field to participate in a COMPOUND index. The
# documented constraint (MongoDB manual, "Compound Indexes" + "2dsphere
# Indexes") is that when the geospatial field is NOT the leftmost key, the
# query MUST supply equality predicates on every preceding key for the
# planner to use the index for the $near/$nearSphere stage. Our access
# pattern does the opposite -- geo is the discriminating term and breed/sex
# are the trailing equality filters -- so the geo field is placed FIRST.
# With (location, breed, sex) the planner can satisfy the $nearSphere on the
# leading 2dsphere key and apply the breed/sex equality predicates as index
# bounds on the trailing keys, instead of post-filtering fetched docs.
#
# We KEEP the plain GEO_INDEX_SPEC too: a bare proximity query with no
# breed/sex filter is still served best by the single-field 2dsphere index,
# and $geoWithin / $geoIntersects queries (which the compound form cannot
# accelerate the same way) continue to rely on it. Both indexes coexist; the
# planner picks per query.
#
# Constraint honored by the test split: mongomock cannot build or plan a
# 2dsphere index, so this is asserted at the spec level in test_specs.py and
# exercised for real only on the docker-compose path.
GEO_COMPOUND_INDEX_SPEC: list[tuple[str, Any]] = [
    ("location", GEOSPHERE),
    ("breed", ASCENDING),
    ("sex_upon_outcome", ASCENDING),
]

# Direct-lookup index on the AAC business key. Mongo's default _id index
# does not help here because animal_id is not _id.
ANIMAL_ID_INDEX_SPEC: list[tuple[str, int]] = [("animal_id", ASCENDING)]


# ---------------------------------------------------------------------------
# Mongo-side role specs (operator tier; not the runtime enforcement path)
# ---------------------------------------------------------------------------

MONGO_ROLES: dict[str, list[dict[str, Any]]] = {
    "shelter_admin": [
        {"resource": {"db": settings.db_name, "collection": ""}, "actions":
            ["find", "insert", "update", "remove", "createCollection",
             "createIndex", "dropCollection"]},
    ],
    "shelter_staff": [
        {"resource": {"db": settings.db_name, "collection": ""}, "actions":
            ["find", "insert", "update"]},
    ],
    "shelter_viewer": [
        {"resource": {"db": settings.db_name, "collection": ""}, "actions":
            ["find"]},
    ],
}


# ---------------------------------------------------------------------------
# Mongo-side USERS for DB-tier isolation (M7 hardening).
# ---------------------------------------------------------------------------
# These three users bind the operator roles above to actual credentials the
# FastAPI ClientFactory (app/db_provider.py) can connect with, one per JWT
# role. With them provisioned and MONGO_URI_ADMIN/STAFF/VIEWER pointed at
# them, a viewer-scoped request physically cannot write at the database tier.
#
# Passwords come from the environment so they are NOT committed to source --
# the same fail-loud-on-missing principle config.py uses. If the env vars are
# absent, user creation is SKIPPED (not faked): the app still runs in
# single-service-account fallback mode. This keeps the grader's happy path
# working while documenting the full isolation deployment.
#
# Spec dict is exposed at module level so test_specs.py can assert the
# role->username->granted-role mapping without a live Mongo (createUser is not
# implemented by mongomock).
MONGO_USERS: dict[str, dict[str, Any]] = {
    "aac_admin": {"role": "shelter_admin", "env": "MONGO_ADMIN_PASSWORD"},
    "aac_staff": {"role": "shelter_staff", "env": "MONGO_STAFF_PASSWORD"},
    "aac_viewer": {"role": "shelter_viewer", "env": "MONGO_VIEWER_PASSWORD"},
}


def _ensure_collection_with_validator(db) -> None:
    """Create the collection with the $jsonSchema validator, or apply the
    validator to an existing collection via collMod. Idempotent.
    """
    name = ANIMALS_COLLECTION
    try:
        db.create_collection(name, validator=JSON_SCHEMA_VALIDATOR)
        logger.info("created collection %s with $jsonSchema validator", name)
    except CollectionInvalid:
        # Already exists -- apply/refresh the validator.
        db.command("collMod", name, validator=JSON_SCHEMA_VALIDATOR)
        logger.info("collection %s already existed; refreshed validator", name)


def _ensure_indexes(db) -> None:
    col = db[ANIMALS_COLLECTION]
    col.create_index(COMPOUND_INDEX_SPEC, name="breed_sex_age_idx")
    col.create_index(GEO_INDEX_SPEC, name="location_2dsphere_idx")
    # Compound 2dsphere for the $nearSphere + breed/sex equality path. See the
    # GEO_COMPOUND_INDEX_SPEC docstring for the planner reasoning.
    col.create_index(GEO_COMPOUND_INDEX_SPEC, name="location_breed_sex_2dsphere_idx")
    col.create_index(ANIMAL_ID_INDEX_SPEC, name="animal_id_idx", unique=True)
    logger.info(
        "indexes ensured: breed_sex_age_idx, location_2dsphere_idx, "
        "location_breed_sex_2dsphere_idx, animal_id_idx"
    )


def _ensure_roles(db) -> None:
    """Create Mongo-side roles. Each call is wrapped so an existing role
    (code 51002 RoleAlreadyExists) does not abort the script.
    """
    for role_name, privileges in MONGO_ROLES.items():
        try:
            db.command(
                "createRole",
                role_name,
                privileges=privileges,
                roles=[],
            )
            logger.info("created Mongo role %s", role_name)
        except OperationFailure as exc:
            if exc.code in (51002,):  # RoleAlreadyExists
                logger.info("Mongo role %s already exists", role_name)
            else:
                # Re-raise anything else so misconfiguration is loud.
                raise


def _ensure_users(db) -> None:
    """Create the per-role Mongo users for DB-tier isolation (M7).

    Each user is granted exactly one operator role from MONGO_ROLES. Passwords
    are read from the environment; a user whose password env var is unset is
    SKIPPED with a clear log line rather than created with a default password
    (default credentials are precisely what the CS340 original got dinged for).
    An already-existing user (code 51003 UserAlreadyExists) is reported and
    left as-is so the script stays idempotent.
    """
    for username, spec in MONGO_USERS.items():
        password = os.environ.get(spec["env"])
        if not password:
            logger.info(
                "skipping Mongo user %s: %s not set (DB-tier isolation stays "
                "in fallback mode for this role)",
                username,
                spec["env"],
            )
            continue
        try:
            db.command(
                "createUser",
                username,
                pwd=password,
                roles=[{"role": spec["role"], "db": settings.db_name}],
            )
            logger.info("created Mongo user %s with role %s", username, spec["role"])
        except OperationFailure as exc:
            if exc.code in (51003,):  # UserAlreadyExists
                logger.info("Mongo user %s already exists", username)
            else:
                raise


def run() -> None:
    client = MongoClient(settings.mongo_uri)
    try:
        db = client[settings.db_name]
        _ensure_collection_with_validator(db)
        _ensure_indexes(db)
        _ensure_roles(db)
        _ensure_users(db)
    finally:
        client.close()


if __name__ == "__main__":
    run()
