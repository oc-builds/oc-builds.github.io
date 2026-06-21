"""Pure spec tests -- no Mongo execution required.

Author: Sanjay Chauhan
Date:   2026-06-07
CS499 Enhancement Three rebuild of the CS340 Austin Animal Center project.

mongomock does not implement $jsonSchema validation, 2dsphere indexes, or
the aggregation operators used here. Rather than skipping the verification
of those features entirely on the sandbox path, we assert directly on the
spec dictionaries that db_setup.py uses and that crud.py builds. If a
grader runs against real Mongo via docker compose, the same dicts get
passed to the real server. If those dicts are right HERE, they are right
THERE.
"""

from __future__ import annotations

from pymongo import ASCENDING, GEOSPHERE

from app import crud
from scripts.db_setup import (
    ANIMAL_ID_INDEX_SPEC,
    COMPOUND_INDEX_SPEC,
    GEO_COMPOUND_INDEX_SPEC,
    GEO_INDEX_SPEC,
    JSON_SCHEMA_VALIDATOR,
    MONGO_ROLES,
    MONGO_USERS,
)


# ---------------------------------------------------------------------------
# $jsonSchema validator shape
# ---------------------------------------------------------------------------


def test_validator_has_required_fields():
    schema = JSON_SCHEMA_VALIDATOR["$jsonSchema"]
    assert schema["bsonType"] == "object"
    assert set(schema["required"]) >= {"animal_id", "animal_type", "location"}


def test_validator_constrains_location_to_geojson_point():
    loc = JSON_SCHEMA_VALIDATOR["$jsonSchema"]["properties"]["location"]
    assert loc["bsonType"] == "object"
    assert set(loc["required"]) == {"type", "coordinates"}
    assert loc["properties"]["type"]["enum"] == ["Point"]
    coords = loc["properties"]["coordinates"]
    assert coords["bsonType"] == "array"
    assert coords["minItems"] == 2
    assert coords["maxItems"] == 2


# ---------------------------------------------------------------------------
# Index specs
# ---------------------------------------------------------------------------


def test_compound_index_ordering_is_breed_sex_age():
    assert COMPOUND_INDEX_SPEC == [
        ("breed", ASCENDING),
        ("sex_upon_outcome", ASCENDING),
        ("age_upon_outcome_in_weeks", ASCENDING),
    ]


def test_geo_index_is_2dsphere_on_location():
    assert GEO_INDEX_SPEC == [("location", GEOSPHERE)]
    # "2dsphere" is the literal string Mongo uses; GEOSPHERE is the pymongo
    # alias. Belt-and-braces: assert the alias resolves to that string.
    assert GEOSPHERE == "2dsphere"


def test_animal_id_index_is_simple_ascending():
    assert ANIMAL_ID_INDEX_SPEC == [("animal_id", ASCENDING)]


def test_geo_compound_index_leads_with_2dsphere_then_breed_sex():
    """M7 hardening: the compound geo index must place the 2dsphere field
    FIRST so a $nearSphere can lead, followed by breed and sex equality keys.

    mongomock cannot plan a 2dsphere index, so we assert the spec shape here
    and rely on the docker-compose path to exercise it for real. The ordering
    is load-bearing: if breed came before location, a bare proximity query
    (no breed filter) could not use the index for the $near stage.
    """
    assert GEO_COMPOUND_INDEX_SPEC == [
        ("location", GEOSPHERE),
        ("breed", ASCENDING),
        ("sex_upon_outcome", ASCENDING),
    ]
    # The geospatial key must be the leftmost element.
    assert GEO_COMPOUND_INDEX_SPEC[0] == ("location", GEOSPHERE)
    # The plain single-field 2dsphere index is preserved, not replaced.
    assert GEO_INDEX_SPEC == [("location", GEOSPHERE)]


# ---------------------------------------------------------------------------
# Aggregation pipeline shape
# ---------------------------------------------------------------------------


def test_breed_aggregation_pipeline_shape():
    pipeline = crud.build_breed_aggregation_pipeline()
    assert isinstance(pipeline, list)
    assert all(isinstance(stage, dict) for stage in pipeline)

    stage_names = [next(iter(stage.keys())) for stage in pipeline]
    assert stage_names == ["$match", "$group", "$sort"]

    match_stage = pipeline[0]["$match"]
    assert "breed" in match_stage

    group_stage = pipeline[1]["$group"]
    assert group_stage["_id"] == "$breed"
    assert group_stage["count"] == {"$sum": 1}

    sort_stage = pipeline[2]["$sort"]
    assert sort_stage == {"count": -1}


# ---------------------------------------------------------------------------
# Mongo-side role specs (operator tier)
# ---------------------------------------------------------------------------


def test_mongo_role_specs_present():
    assert set(MONGO_ROLES.keys()) == {
        "shelter_admin",
        "shelter_staff",
        "shelter_viewer",
    }
    # viewer must NOT have insert/update/remove.
    viewer_actions = set()
    for priv in MONGO_ROLES["shelter_viewer"]:
        viewer_actions.update(priv["actions"])
    assert "find" in viewer_actions
    assert not (viewer_actions & {"insert", "update", "remove"})

    # admin must have remove (delete) privileges.
    admin_actions = set()
    for priv in MONGO_ROLES["shelter_admin"]:
        admin_actions.update(priv["actions"])
    assert "remove" in admin_actions


def test_mongo_users_map_each_role_to_operator_role():
    """M7 DB-tier isolation: three Mongo users, one per JWT role, each bound
    to the matching operator role. Asserted at spec level because mongomock
    does not implement createUser.
    """
    assert set(MONGO_USERS.keys()) == {"aac_admin", "aac_staff", "aac_viewer"}
    assert MONGO_USERS["aac_admin"]["role"] == "shelter_admin"
    assert MONGO_USERS["aac_staff"]["role"] == "shelter_staff"
    assert MONGO_USERS["aac_viewer"]["role"] == "shelter_viewer"
    # Every granted role must be a real role defined in MONGO_ROLES.
    for spec in MONGO_USERS.values():
        assert spec["role"] in MONGO_ROLES
        # Passwords must come from the environment, never be hard-coded.
        assert "env" in spec and spec["env"]
