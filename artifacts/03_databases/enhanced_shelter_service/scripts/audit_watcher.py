"""Change-stream audit watcher -- defense-in-depth for the audit log.

Author: Sanjay Chauhan
Date:   2026-06-20
CS499 Enhancement Three (Module 7 hardening) for the CS340 Austin Animal
Center project.

WHY THIS EXISTS
---------------
The application's audit guarantee rests on the Repository.save_with_audit()
chokepoint in app/db.py: every write that flows through the API also writes
an audit_log entry in the same call. That holds for ANY traffic that goes
through the FastAPI process. It does NOT hold for a write made directly
against MongoDB -- an operator with a mongosh shell or a stray PyMongo
script can mutate animals_geo and never touch audit_log. The existing
negative test (test_direct_write_does_not_produce_audit_entry) proves that
gap exists by construction.

This watcher closes the gap from the database side. It opens a MongoDB
change stream on the animals_geo collection and, for every insert / update /
replace / delete that arrives, checks whether a corresponding audit_log
entry already exists (i.e. the chokepoint already recorded it). If none is
found, the change bypassed the chokepoint, so the watcher writes a
catch-up audit entry tagged source="change_stream_watcher". The result is
that EVERY state change to animals_geo ends up in audit_log, whether it
came through the API or around it.

HONEST FRAMING (Dr. Bolton has a database background)
-----------------------------------------------------
- A true server-side trigger (Atlas Triggers / Realm functions) is NOT
  available on self-hosted Mongo. The honest, self-hostable equivalent is
  this change-stream consumer running as a sidecar process. It is
  eventually-consistent, not transactional: there is a small window between
  the operational write and the catch-up audit entry. That is a real
  limitation, stated plainly, not papered over.
- Change streams REQUIRE the mongod to run as a replica set (even a
  single-node replica set). The default docker-compose standalone Mongo
  does NOT emit change streams; see README "Hardening (Module 7)" for the
  one-line compose change (`--replSet rs0`) and the rs.initiate() step.
- The watcher de-duplicates against existing chokepoint entries so a normal
  API write is not double-audited. The correlation is best-effort by
  (target_collection, target_id) within a short time window; in a
  high-throughput system you would carry a correlation id on the document
  instead. For this single-host shelter service the window heuristic is
  adequate and is documented as such.

The pure decision logic (needs_catch_up_audit) is factored out so it can be
unit-tested without a live replica set. The streaming loop (run_watcher)
needs a real Mongo and is exercised on the docker-compose path only.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import OperationFailure, PyMongoError

# Allow running directly: `python3 scripts/audit_watcher.py`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("audit_watcher")


# Default correlation window. A chokepoint audit entry written within this
# many seconds of the change event is treated as "already audited". Tuned for
# a single-host demo where clock skew between the API process and the watcher
# is negligible; documented in the module docstring.
DEFAULT_CORRELATION_WINDOW_SECONDS = 30


def _extract_target_id(change: Mapping[str, Any]) -> Optional[str]:
    """Pull the business key (animal_id) from a change-stream event.

    For insert/replace the full document is present under fullDocument. For
    update we may only get updateDescription unless fullDocument lookup is
    enabled; for delete we only have documentKey (_id). We prefer animal_id
    because that is what the chokepoint records as target_id; we fall back to
    the stringified _id so a delete event still correlates on something.
    """
    full = change.get("fullDocument")
    if isinstance(full, Mapping) and full.get("animal_id"):
        return str(full["animal_id"])
    key = change.get("documentKey")
    if isinstance(key, Mapping) and "_id" in key:
        return str(key["_id"])
    return None


def needs_catch_up_audit(
    *,
    audit_col: Collection,
    target_collection: str,
    target_id: Optional[str],
    event_time: datetime,
    window_seconds: int = DEFAULT_CORRELATION_WINDOW_SECONDS,
) -> bool:
    """Pure decision: should the watcher write a catch-up audit entry?

    Returns True when NO chokepoint audit entry exists for this
    (target_collection, target_id) inside [event_time - window, now]. That
    absence means the change bypassed save_with_audit() and must be recorded
    from the database side.

    Why a time window rather than an exact match: the chokepoint does not
    stamp a correlation id onto the operational document, so the only honest
    correlation available is "an audit entry for the same target landed at
    about the same time". A wider window risks missing a genuinely
    un-audited change that happens to follow a legitimate one; a narrower
    window risks double-auditing. The default is deliberately small and the
    trade-off is documented. This function is unit-tested against mongomock
    because it is plain find logic with no change-stream dependency.
    """
    if target_id is None:
        # No key to correlate on -> safest to record it; an un-keyed direct
        # write is exactly the kind of thing the audit log should capture.
        return True

    since = event_time - timedelta(seconds=window_seconds)
    existing = audit_col.find_one(
        {
            "target_collection": target_collection,
            "target_id": target_id,
            "timestamp": {"$gte": since},
        }
    )
    return existing is None


def _write_catch_up_entry(
    audit_col: Collection,
    *,
    operation: str,
    target_collection: str,
    target_id: Optional[str],
    after: Optional[dict[str, Any]],
) -> None:
    """Persist a catch-up audit entry tagged with its out-of-band source.

    The `source` field distinguishes watcher-generated entries from chokepoint
    entries so a reviewer can immediately see which writes went around the
    API. `user` is "<unknown:direct-db-write>" because a direct DB mutation
    carries no authenticated identity -- claiming otherwise would be dishonest.
    """
    audit_col.insert_one(
        {
            "user": "<unknown:direct-db-write>",
            "action": f"direct_{operation}",
            "target_collection": target_collection,
            "target_id": target_id,
            "timestamp": datetime.now(timezone.utc),
            "before": None,
            # The watcher cannot reconstruct a true before-image for an
            # out-of-band write; it records the after-image when available.
            "after": after,
            "source": "change_stream_watcher",
        }
    )


def run_watcher(client: MongoClient, *, window_seconds: int = DEFAULT_CORRELATION_WINDOW_SECONDS) -> None:
    """Tail the animals_geo change stream forever, back-filling missing audits.

    REQUIRES a replica-set Mongo (change streams are unavailable on a
    standalone mongod). On a standalone server pymongo raises OperationFailure
    with a clear message; we surface that rather than silently no-op'ing,
    because a watcher that appears to run but cannot see changes would be a
    false sense of security -- the opposite of the hardening goal.
    """
    db = client[settings.db_name]
    animals = db[settings.animals_collection]
    audit_col = db[settings.audit_collection]

    logger.info(
        "audit watcher starting on %s.%s (correlation window=%ss)",
        settings.db_name,
        settings.animals_collection,
        window_seconds,
    )
    try:
        # full_document="updateLookup" so update events carry the post-image,
        # letting us extract animal_id and store a meaningful after-snapshot.
        with animals.watch(full_document="updateLookup") as stream:
            for change in stream:
                _handle_change(change, audit_col=audit_col, window_seconds=window_seconds)
    except OperationFailure as exc:
        logger.error(
            "change stream unavailable: %s. Mongo must run as a replica set "
            "(e.g. mongod --replSet rs0 then rs.initiate()). See README "
            "'Hardening (Module 7)'.",
            exc,
        )
        raise
    except PyMongoError:
        logger.exception("audit watcher stopped on a Mongo error")
        raise


def _handle_change(
    change: Mapping[str, Any],
    *,
    audit_col: Collection,
    window_seconds: int,
) -> bool:
    """Process one change event. Returns True if a catch-up entry was written.

    Split out from run_watcher so the per-event behavior is independently
    testable: a caller can hand it a synthetic change dict plus a mongomock
    audit collection and assert on the outcome without a live change stream.
    """
    op = change.get("operationType", "unknown")
    # We only audit state-changing ops. 'invalidate'/'drop'/etc. are stream
    # lifecycle events, not document mutations.
    if op not in {"insert", "update", "replace", "delete"}:
        return False

    target_id = _extract_target_id(change)
    event_time = datetime.now(timezone.utc)

    if not needs_catch_up_audit(
        audit_col=audit_col,
        target_collection=settings.animals_collection,
        target_id=target_id,
        event_time=event_time,
        window_seconds=window_seconds,
    ):
        # A chokepoint entry already covers this change; nothing to do.
        return False

    after = change.get("fullDocument")
    after_dict = dict(after) if isinstance(after, Mapping) else None
    if after_dict is not None and "_id" in after_dict:
        after_dict["_id"] = str(after_dict["_id"])

    _write_catch_up_entry(
        audit_col,
        operation=op,
        target_collection=settings.animals_collection,
        target_id=target_id,
        after=after_dict,
    )
    logger.warning(
        "back-filled audit for un-chokepointed %s on target_id=%s",
        op,
        target_id,
    )
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--window-seconds",
        type=int,
        default=DEFAULT_CORRELATION_WINDOW_SECONDS,
        help="correlation window for de-duplicating against chokepoint audits",
    )
    args = parser.parse_args()

    client = MongoClient(settings.mongo_uri)
    try:
        run_watcher(client, window_seconds=args.window_seconds)
    finally:
        client.close()


if __name__ == "__main__":
    main()
