"""Unit tests for the change-stream audit watcher decision logic (M7).

Author: Sanjay Chauhan
Date:   2026-06-20
CS499 Enhancement Three (Module 7 hardening) for the CS340 Austin Animal
Center project.

The change stream itself REQUIRES a replica-set Mongo and cannot run under
mongomock, so the streaming loop (run_watcher) is exercised only on the
docker-compose path. What we CAN and DO test here is the pure decision logic
that decides whether a change needs a catch-up audit entry, plus the
per-event handler -- both of which are plain find/insert operations that
mongomock supports. That is the part where a bug would actually let a direct
write slip past unaudited, so it is the part worth pinning down with tests.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import mongomock

from app.config import settings
from scripts import audit_watcher


def _audit_col():
    client = mongomock.MongoClient()
    return client[settings.db_name][settings.audit_collection]


def test_needs_catch_up_true_when_no_prior_audit():
    """A direct write with no matching chokepoint entry -> needs catch-up."""
    col = _audit_col()
    assert (
        audit_watcher.needs_catch_up_audit(
            audit_col=col,
            target_collection=settings.animals_collection,
            target_id="A777",
            event_time=datetime.now(timezone.utc),
        )
        is True
    )


def test_needs_catch_up_false_when_chokepoint_entry_recent():
    """A normal API write already left an audit entry -> no double audit."""
    col = _audit_col()
    now = datetime.now(timezone.utc)
    col.insert_one(
        {
            "user": "alice",
            "action": "create_animal",
            "target_collection": settings.animals_collection,
            "target_id": "A777",
            "timestamp": now,
        }
    )
    assert (
        audit_watcher.needs_catch_up_audit(
            audit_col=col,
            target_collection=settings.animals_collection,
            target_id="A777",
            event_time=now,
        )
        is False
    )


def test_needs_catch_up_true_when_prior_audit_is_outside_window():
    """An old audit entry for the same id must NOT suppress a new change."""
    col = _audit_col()
    old = datetime.now(timezone.utc) - timedelta(hours=2)
    col.insert_one(
        {
            "user": "alice",
            "action": "create_animal",
            "target_collection": settings.animals_collection,
            "target_id": "A777",
            "timestamp": old,
        }
    )
    assert (
        audit_watcher.needs_catch_up_audit(
            audit_col=col,
            target_collection=settings.animals_collection,
            target_id="A777",
            event_time=datetime.now(timezone.utc),
            window_seconds=30,
        )
        is True
    )


def test_needs_catch_up_true_when_target_id_unknown():
    """An un-keyed change (e.g. delete with only _id we cannot map) is
    recorded rather than silently dropped."""
    col = _audit_col()
    assert (
        audit_watcher.needs_catch_up_audit(
            audit_col=col,
            target_collection=settings.animals_collection,
            target_id=None,
            event_time=datetime.now(timezone.utc),
        )
        is True
    )


def test_handle_change_backfills_unaudited_insert():
    """An insert event with no chokepoint entry produces a tagged catch-up."""
    col = _audit_col()
    change = {
        "operationType": "insert",
        "fullDocument": {
            "_id": "abc",
            "animal_id": "DIRECT-1",
            "breed": "X",
        },
        "documentKey": {"_id": "abc"},
    }
    wrote = audit_watcher._handle_change(change, audit_col=col, window_seconds=30)
    assert wrote is True
    entry = col.find_one({"target_id": "DIRECT-1"})
    assert entry is not None
    assert entry["source"] == "change_stream_watcher"
    assert entry["action"] == "direct_insert"
    assert entry["user"] == "<unknown:direct-db-write>"
    # _id is stringified in the stored after-image.
    assert entry["after"]["animal_id"] == "DIRECT-1"


def test_handle_change_skips_already_audited():
    """A change already covered by a chokepoint entry is left alone."""
    col = _audit_col()
    now = datetime.now(timezone.utc)
    col.insert_one(
        {
            "user": "alice",
            "action": "create_animal",
            "target_collection": settings.animals_collection,
            "target_id": "API-1",
            "timestamp": now,
        }
    )
    change = {
        "operationType": "insert",
        "fullDocument": {"_id": "x", "animal_id": "API-1"},
        "documentKey": {"_id": "x"},
    }
    wrote = audit_watcher._handle_change(change, audit_col=col, window_seconds=30)
    assert wrote is False
    # Still exactly one entry: the original chokepoint one, no watcher dup.
    assert col.count_documents({"target_id": "API-1"}) == 1


def test_handle_change_ignores_non_mutation_events():
    """Stream lifecycle events (e.g. invalidate) are not audited."""
    col = _audit_col()
    wrote = audit_watcher._handle_change(
        {"operationType": "invalidate"}, audit_col=col, window_seconds=30
    )
    assert wrote is False
    assert col.count_documents({}) == 0


def test_extract_target_id_prefers_animal_id_then_falls_back_to_id():
    assert (
        audit_watcher._extract_target_id(
            {"fullDocument": {"animal_id": "A1"}, "documentKey": {"_id": "z"}}
        )
        == "A1"
    )
    # delete events carry only documentKey
    assert (
        audit_watcher._extract_target_id({"documentKey": {"_id": "z"}}) == "z"
    )
    assert audit_watcher._extract_target_id({}) is None
