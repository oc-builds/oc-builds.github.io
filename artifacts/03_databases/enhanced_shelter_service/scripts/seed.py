"""Seed demo users and a 200-row animals_geo fixture.

Author: Sanjay Chauhan
Date:   2026-06-07
CS499 Enhancement Three rebuild of the CS340 Austin Animal Center project.

GRADING ONLY -- the three demo passwords below are documented and committed
on purpose so Dr. Bolton can log in without a credential exchange. Rotate
them before any non-grading use. The hashed values are NEVER printed and
never returned by any API endpoint.

Idempotent: re-running the script upserts each user (no duplicate creation)
and upserts each fixture row keyed on animal_id.
"""

from __future__ import annotations

import csv
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.auth import hash_password  # noqa: E402
from app.config import settings  # noqa: E402
from app.models import Role  # noqa: E402
from scripts.migrate_geojson import to_geojson  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("seed")


# GRADING ONLY -- rotate before any real use.
DEMO_USERS: list[dict[str, str]] = [
    {"username": "admin", "password": "Admin#Demo2026!", "role": Role.ADMIN.value},
    {"username": "staff", "password": "Staff#Demo2026!", "role": Role.STAFF.value},
    {"username": "viewer", "password": "Viewer#Demo2026!", "role": Role.VIEWER.value},
]

# Default CSV fixture path: looks in the local ./data folder first, then falls back to
# an env-override so a grader can point at any location without code edits.
# Why: an absolute path hard-coded to one developer's machine would silently no-op on a
# grader's machine; the env override keeps the script portable while the default supports
# the convention used in the original CS340 layout.
_DEFAULT_CSV = Path(__file__).resolve().parent.parent / "data" / "aac_shelter_outcomes.csv"
CSV_PATH = Path(os.environ.get("SEED_CSV_PATH", _DEFAULT_CSV))
FIXTURE_LIMIT = 200


def seed_users(db) -> None:
    users = db[settings.users_collection]
    for row in DEMO_USERS:
        users.update_one(
            {"username": row["username"]},
            {
                "$set": {
                    "username": row["username"],
                    "password_hash": hash_password(row["password"]),
                    "role": row["role"],
                }
            },
            upsert=True,
        )
    logger.info("upserted %d demo users", len(DEMO_USERS))


def _coerce_float(value: str) -> Optional[float]:
    if value in (None, "", "NULL"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def seed_fixture(db, csv_path: Path = CSV_PATH, limit: int = FIXTURE_LIMIT) -> int:
    """Load up to `limit` rows from the CSV into animals_geo with GeoJSON.

    Returns the number of rows actually upserted.
    """
    if not csv_path.exists():
        logger.warning("csv not found at %s -- skipping fixture load", csv_path)
        return 0

    animals = db[settings.animals_collection]
    inserted = 0
    skipped = 0
    with csv_path.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if inserted >= limit:
                break
            lon = _coerce_float(row.get("location_long", ""))
            lat = _coerce_float(row.get("location_lat", ""))
            point = to_geojson(lon, lat)
            if point is None:
                skipped += 1
                continue

            doc = {
                "animal_id": row.get("animal_id"),
                "animal_type": row.get("animal_type"),
                "breed": row.get("breed"),
                "color": row.get("color") or None,
                "name": row.get("name") or None,
                "sex_upon_outcome": row.get("sex_upon_outcome") or None,
                "age_upon_outcome": row.get("age_upon_outcome") or None,
                "age_upon_outcome_in_weeks": _coerce_float(
                    row.get("age_upon_outcome_in_weeks", "")
                ),
                "outcome_type": row.get("outcome_type") or None,
                "outcome_subtype": row.get("outcome_subtype") or None,
                "date_of_birth": row.get("date_of_birth") or None,
                "datetime": row.get("datetime") or None,
                "monthyear": row.get("monthyear") or None,
                "location": point,
            }
            if not doc["animal_id"] or not doc["animal_type"]:
                skipped += 1
                continue

            animals.update_one(
                {"animal_id": doc["animal_id"]},
                {"$set": doc},
                upsert=True,
            )
            inserted += 1

    logger.info("fixture load: inserted=%d skipped=%d", inserted, skipped)
    return inserted


def run() -> None:
    client = MongoClient(settings.mongo_uri)
    try:
        db = client[settings.db_name]
        seed_users(db)
        seed_fixture(db)
    finally:
        client.close()


if __name__ == "__main__":
    run()
