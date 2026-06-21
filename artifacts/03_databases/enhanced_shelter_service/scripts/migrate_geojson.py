"""Two-pass migration: animals -> animals_geo with GeoJSON coordinates.

Author: Sanjay Chauhan
Date:   2026-06-07
CS499 Enhancement Three rebuild of the CS340 Austin Animal Center project.

Why a two-pass copy rather than an in-place rewrite: the original
`animals` collection stays untouched so the M4 narrative can demonstrate
the before/after without losing the source. animals_geo carries the
GeoJSON Point field and is the collection the validator + 2dsphere index
target.

GeoJSON coordinate order is [longitude, latitude]. The original CSV
stored location_lat then location_long as separate columns, and the
notebook read them by positional index. We flip the order ONCE here with
explicit range assertions per doc so a transposed pair fails loudly
rather than silently producing nonsense maps.

Docs that fail the range check are skipped and logged. We do not abort
the whole migration on a single bad row -- that would be a poor experience
on 10k records where one outlier could halt everything. The summary line
at the end prints copied / skipped counts.
"""

from __future__ import annotations

import logging
import sys
from typing import Any, Optional

from pymongo import MongoClient

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("migrate_geojson")

SOURCE_COLLECTION = "animals"
TARGET_COLLECTION = settings.animals_collection


def to_geojson(
    lon: Optional[float], lat: Optional[float]
) -> Optional[dict[str, Any]]:
    """Return a GeoJSON Point dict or None if coordinates are unusable.

    Range checks: lon in [-180, 180], lat in [-90, 90]. The migration logs
    and skips rather than asserting because real-world data has outliers
    and we want to surface them, not crash on the first one.
    """
    if lon is None or lat is None:
        return None
    try:
        lon_f = float(lon)
        lat_f = float(lat)
    except (TypeError, ValueError):
        return None
    if not (-180.0 <= lon_f <= 180.0 and -90.0 <= lat_f <= 90.0):
        return None
    return {"type": "Point", "coordinates": [lon_f, lat_f]}


def run() -> None:
    client = MongoClient(settings.mongo_uri)
    try:
        db = client[settings.db_name]
        source = db[SOURCE_COLLECTION]
        target = db[TARGET_COLLECTION]

        copied = 0
        skipped = 0
        for doc in source.find({}):
            lon = doc.get("location_long")
            lat = doc.get("location_lat")
            point = to_geojson(lon, lat)
            if point is None:
                skipped += 1
                logger.warning(
                    "skipping animal_id=%s: bad coords lon=%r lat=%r",
                    doc.get("animal_id"),
                    lon,
                    lat,
                )
                continue

            new_doc = {k: v for k, v in doc.items() if k != "_id"}
            new_doc["location"] = point
            # upsert keyed on animal_id so re-running the migration is
            # idempotent.
            target.update_one(
                {"animal_id": new_doc.get("animal_id")},
                {"$set": new_doc},
                upsert=True,
            )
            copied += 1

        logger.info("migration complete: copied=%d skipped=%d", copied, skipped)
    finally:
        client.close()


if __name__ == "__main__":
    run()
