"""Animal CRUD, geospatial proximity, and aggregation.

Author: Sanjay Chauhan
Date:   2026-06-07
CS499 Enhancement Three rebuild of the CS340 Austin Animal Center project.

Single-responsibility: routes call into this module. This module never
imports FastAPI or JWT machinery. Every write goes through
Repository.save_with_audit(); reads go through the repository's read
helpers. The Mongo collection handle itself never leaves the repository.

Index strategy (the WHY for each one is repeated here AND in db_setup.py
where the index is actually created, because both files are reviewed):

  - Compound (breed, sex_upon_outcome, age_upon_outcome_in_weeks):
    Every rescue-category filter restricts breed first, frequently
    restricts sex second, and only sometimes restricts age. Mongo's
    leftmost-prefix rule means the same index serves {breed},
    {breed, sex}, and {breed, sex, age} queries. Putting the
    most-selective column first would seem natural, but the rescue
    queries do NOT have a single most-selective column -- they ALWAYS
    include breed, so breed must be the leftmost prefix.

  - 2dsphere on `location` (the GeoJSON Point field):
    The original notebook computed distance in Python from two scalar
    columns. A 2dsphere index turns proximity queries into O(log n)
    instead of O(n) -- this is one of the explicit Outcome 3 trade-offs
    the narrative cites.

  - Single ascending on animal_id:
    Direct-lookup endpoint /animals/{animal_id} needs an indexed equality
    match. The Mongo default _id index does not cover animal_id because
    animal_id is the AAC business key, not Mongo's ObjectId.

Rescue-category filter mapping is derived from the original notebook's
four filter callbacks. The strings ("breed A", "breed B", ...) match what
the original dashboard used so the dataset selects the same animals.
"""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

from .db import Repository
from .models import (
    Animal,
    AnimalCreate,
    AnimalUpdate,
    RescueCategory,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rescue-category filter map. Pulled from the original CS340 ProjectTwo
# dashboard callbacks. The category -> {breed in [...], sex_upon_outcome,
# age_upon_outcome_in_weeks range} mapping is the domain knowledge of the
# original project; the narrative cites this as a preserved business rule.
# ---------------------------------------------------------------------------

_RESCUE_FILTERS: dict[RescueCategory, dict[str, Any]] = {
    RescueCategory.WATER: {
        "breed": {
            "$in": [
                "Labrador Retriever Mix",
                "Chesa Bay Retr Mix",
                "Newfoundland Mix",
            ]
        },
        "sex_upon_outcome": "Intact Female",
        "age_upon_outcome_in_weeks": {"$gte": 26.0, "$lte": 156.0},
    },
    RescueCategory.MOUNTAIN: {
        "breed": {
            "$in": [
                "German Shepherd",
                "Alaskan Malamute",
                "Old English Sheepdog",
                "Siberian Husky",
                "Rottweiler",
            ]
        },
        "sex_upon_outcome": "Intact Male",
        "age_upon_outcome_in_weeks": {"$gte": 26.0, "$lte": 156.0},
    },
    RescueCategory.DISASTER: {
        "breed": {
            "$in": [
                "Doberman Pinscher",
                "German Shepherd",
                "Golden Retriever",
                "Bloodhound",
                "Rottweiler",
            ]
        },
        "sex_upon_outcome": "Intact Male",
        "age_upon_outcome_in_weeks": {"$gte": 20.0, "$lte": 300.0},
    },
}


def _build_filter(
    *,
    breed: Optional[str],
    sex: Optional[str],
    rescue: Optional[RescueCategory],
) -> dict[str, Any]:
    """Compose a Mongo filter dict from optional query parameters.

    Why this is its own function: tests can call it directly and assert on
    the filter shape without touching the database. The compound index is
    only useful if our filters actually hit it, so verifying the dict shape
    is part of the index-correctness argument.
    """
    if rescue is not None:
        # Rescue category overrides ad-hoc breed/sex because the category
        # IS a curated combination of breed + sex + age. Mixing both would
        # produce confusing queries.
        return dict(_RESCUE_FILTERS[rescue])

    flt: dict[str, Any] = {}
    if breed:
        flt["breed"] = breed
    if sex:
        flt["sex_upon_outcome"] = sex
    return flt


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


def list_animals(
    repo: Repository,
    *,
    breed: Optional[str] = None,
    sex: Optional[str] = None,
    rescue: Optional[RescueCategory] = None,
    skip: int = 0,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Paginated, filtered list. Replaces the original `db.read({})` that
    loaded all 10k rows into memory.
    """
    flt = _build_filter(breed=breed, sex=sex, rescue=rescue)
    docs = repo.find_animals(flt, skip=skip, limit=limit)
    return [_normalize(d) for d in docs]


def get_animal(repo: Repository, animal_id: str) -> Optional[dict[str, Any]]:
    doc = repo.find_one_animal({"animal_id": animal_id})
    return _normalize(doc) if doc else None


def find_near(
    repo: Repository,
    *,
    lon: float,
    lat: float,
    max_meters: float,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """2dsphere proximity query. The original computed Haversine in Python
    after pulling rows; Mongo's $nearSphere uses the 2dsphere index and is
    O(log n) on the index lookup plus O(k) on results.

    `$maxDistance` for $nearSphere on GeoJSON points is in meters per the
    Mongo docs. The API surface accepts kilometers (more humane for the
    rescue use case) and converts upstream.
    """
    query = {
        "location": {
            "$nearSphere": {
                "$geometry": {"type": "Point", "coordinates": [lon, lat]},
                "$maxDistance": max_meters,
            }
        }
    }
    docs = list(repo.animals.find(query).limit(limit))
    return [_normalize(d) for d in docs]


def aggregate_by_breed(repo: Repository) -> list[dict[str, Any]]:
    """Aggregation: count per breed, descending. Replaces the pandas
    `value_counts()` the original computed AFTER loading all rows. This
    runs server-side and returns just the counts.
    """
    pipeline = build_breed_aggregation_pipeline()
    return repo.aggregate(pipeline)


def build_breed_aggregation_pipeline() -> list[dict[str, Any]]:
    """Exposed for tests so the pipeline shape can be asserted directly."""
    # $match drops documents that lack a breed so the $group key is never
    # null; $group counts per breed; $sort surfaces the most common breeds
    # first because that is what the original pie chart highlighted.
    return [
        {"$match": {"breed": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": "$breed", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]


# ---------------------------------------------------------------------------
# Write -- all via the chokepoint
# ---------------------------------------------------------------------------


def create_animal(
    repo: Repository,
    payload: AnimalCreate,
    *,
    user: str,
    collection_name: str,
) -> dict[str, Any]:
    return repo.save_with_audit(
        user=user,
        action="create_animal",
        collection_name=collection_name,
        target_id=payload.animal_id,
        operation="insert",
        payload=payload.model_dump(),
    )


def update_animal(
    repo: Repository,
    animal_id: str,
    patch: AnimalUpdate,
    *,
    user: str,
    collection_name: str,
) -> dict[str, Any]:
    # exclude_unset so a partial update does not overwrite fields with None
    # just because the caller did not pass them.
    payload = patch.model_dump(exclude_unset=True)
    if not payload:
        raise ValueError("update payload is empty")
    return repo.save_with_audit(
        user=user,
        action="update_animal",
        collection_name=collection_name,
        target_id=animal_id,
        operation="update",
        filter_={"animal_id": animal_id},
        payload=payload,
    )


def delete_animal(
    repo: Repository,
    animal_id: str,
    *,
    user: str,
    collection_name: str,
) -> dict[str, Any]:
    return repo.save_with_audit(
        user=user,
        action="delete_animal",
        collection_name=collection_name,
        target_id=animal_id,
        operation="delete",
        filter_={"animal_id": animal_id},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize(doc: Optional[Mapping[str, Any]]) -> Optional[dict[str, Any]]:
    """Stringify _id so it serializes as JSON cleanly."""
    if doc is None:
        return None
    out = dict(doc)
    if "_id" in out:
        out["_id"] = str(out["_id"])
    return out
