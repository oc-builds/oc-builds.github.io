"""MongoDB client wrapper and the Repository chokepoint for all writes.

Author: Sanjay Chauhan
Date:   2026-06-07
CS499 Enhancement Three rebuild of the CS340 Austin Animal Center project.

The chokepoint pattern: every create/update/delete in this codebase MUST
flow through Repository.save_with_audit(). That single method is the only
place a write touches the operational collection AND the audit_log
collection in the same call. Routes do not call PyMongo directly; CRUD
helpers compose into Repository methods; tests verify (a) the audit entry
exists when the chokepoint is used, and (b) a direct write that bypasses
the chokepoint does NOT produce an audit entry, which is the negative test
that proves the property.

The Mongo client is owned by the FastAPI `lifespan` context (see main.py)
and passed into route handlers via Depends. There is no module-global
client. This matters for two reasons: (1) tests can swap in a mongomock
client cleanly, (2) clean shutdown is guaranteed -- the original notebook
leaked connections when re-run.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Optional

from pymongo.collection import Collection
from pymongo.database import Database

from .audit import AuditWriter

logger = logging.getLogger(__name__)


class Repository:
    """The single write path for the application.

    Holds references to the operational collection (animals_geo), the users
    collection, and an AuditWriter for the audit_log collection. Constructed
    from a pymongo Database handle so the same class works against a real
    Mongo client or a mongomock client without modification.
    """

    def __init__(
        self,
        db: Database,
        *,
        animals_collection: str,
        users_collection: str,
        audit_collection: str,
    ) -> None:
        self._db = db
        self.animals: Collection = db[animals_collection]
        self.users: Collection = db[users_collection]
        self._audit = AuditWriter(db[audit_collection])
        self._animals_name = animals_collection

    # ------------------------------------------------------------------
    # Read paths -- no audit, no chokepoint, by design.
    # ------------------------------------------------------------------

    def find_animals(
        self,
        filter_: Mapping[str, Any],
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        cursor = self.animals.find(filter_).skip(skip).limit(limit)
        return list(cursor)

    def find_one_animal(self, filter_: Mapping[str, Any]) -> Optional[dict[str, Any]]:
        return self.animals.find_one(filter_)

    def aggregate(self, pipeline: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
        return list(self.animals.aggregate(pipeline))

    # ------------------------------------------------------------------
    # Write chokepoint -- every state-changing operation lives here.
    # ------------------------------------------------------------------

    def save_with_audit(
        self,
        *,
        user: str,
        action: str,
        collection_name: str,
        target_id: Optional[str],
        operation: str,
        payload: Optional[Mapping[str, Any]] = None,
        filter_: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, Any]:
        """Execute a write and journal it in the same call.

        Why one method covering all four operations: this lets us prove by
        construction that no write is missed. Splitting create/update/delete
        into separate writers would re-introduce the gap where someone
        could call `collection.update_one(...)` directly and forget the
        audit hook.

        operation is one of: "insert", "update", "delete".

        Returns a dict with the result and an `audited` flag the caller can
        assert on in tests. The audit entry includes redacted before/after
        snapshots (see audit.py for the redaction rules).
        """
        col = self._db[collection_name]
        before: Optional[dict[str, Any]] = None
        after: Optional[dict[str, Any]] = None
        result: dict[str, Any] = {}

        if operation == "insert":
            if payload is None:
                raise ValueError("insert requires payload")
            insert_result = col.insert_one(dict(payload))
            inserted_id = str(insert_result.inserted_id)
            after = col.find_one({"_id": insert_result.inserted_id})
            result = {"inserted_id": inserted_id}
            audit_target = target_id or inserted_id

        elif operation == "update":
            if filter_ is None or payload is None:
                raise ValueError("update requires filter_ and payload")
            before = col.find_one(filter_)
            update_result = col.update_one(filter_, {"$set": dict(payload)})
            after = col.find_one(filter_)
            result = {
                "matched": update_result.matched_count,
                "modified": update_result.modified_count,
            }
            audit_target = target_id

        elif operation == "delete":
            if filter_ is None:
                raise ValueError("delete requires filter_")
            before = col.find_one(filter_)
            delete_result = col.delete_one(filter_)
            result = {"deleted": delete_result.deleted_count}
            audit_target = target_id

        else:
            raise ValueError(f"unknown operation: {operation!r}")

        self._audit.record(
            user=user,
            action=action,
            target_collection=collection_name,
            target_id=audit_target,
            before=before,
            after=after,
        )
        result["audited"] = True
        return result

    # ------------------------------------------------------------------
    # User lookup (read-only; auth.py owns user creation through the
    # same chokepoint above with collection_name=users).
    # ------------------------------------------------------------------

    def find_user(self, username: str) -> Optional[dict[str, Any]]:
        return self.users.find_one({"username": username})


def build_repository(
    db: Database,
    *,
    animals_collection: str,
    users_collection: str,
    audit_collection: str,
) -> Repository:
    """Factory used by the FastAPI lifespan and by tests."""
    return Repository(
        db,
        animals_collection=animals_collection,
        users_collection=users_collection,
        audit_collection=audit_collection,
    )
