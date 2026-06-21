"""Audit log writer.

Author: Sanjay Chauhan
Date:   2026-06-07
CS499 Enhancement Three rebuild of the CS340 Austin Animal Center project.

Redaction policy: any field whose name matches the case-insensitive pattern
^(password|token|secret) is stripped from `before` and `after` snapshots
before they are persisted. Plain JWTs, bcrypt hashes, and named secrets must
never appear in audit_log. This is enforced here, in the only writer, so a
careless caller cannot accidentally journal credentials.

The AuditWriter is intentionally a thin object that knows nothing about
animals -- it can audit any collection. It is invoked ONLY from the
Repository chokepoint in db.py. Routes and CRUD functions never call this
directly. That single-writer rule is what makes the audit log trustworthy:
if a record was written without an audit entry, the chokepoint was bypassed,
and that is a code-review-time bug, not a runtime configuration question.
"""

from __future__ import annotations

import copy
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from pymongo.collection import Collection

logger = logging.getLogger(__name__)


# Case-insensitive match against field names. The pattern is deliberately
# anchored at the start so a benign field like `description` does not get
# stripped just because it happens to contain the substring "secret".
_SENSITIVE_NAME = re.compile(r"^(password|token|secret)", re.IGNORECASE)


def _redact(snapshot: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Deep-copy and remove sensitive keys.

    Deep copy is required because we must not mutate the caller's document.
    The cost is one extra walk per audited write -- negligible compared to
    the network round-trip to Mongo.
    """
    if snapshot is None:
        return None

    cleaned = copy.deepcopy(snapshot)

    def _walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for key in list(obj.keys()):
                if _SENSITIVE_NAME.match(key):
                    del obj[key]
                else:
                    _walk(obj[key])
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(cleaned)
    return cleaned


class AuditWriter:
    """Persist audit entries to the audit_log collection."""

    def __init__(self, audit_collection: Collection) -> None:
        self._col = audit_collection

    def record(
        self,
        *,
        user: str,
        action: str,
        target_collection: str,
        target_id: Optional[str],
        before: Optional[dict[str, Any]] = None,
        after: Optional[dict[str, Any]] = None,
    ) -> None:
        """Insert a single audit entry. Never raises -- a failure to journal
        is logged but does not block the operational write. Why: dropping
        audit entries on the floor would be worse than logging the failure
        and continuing, but only because the chokepoint pattern catches
        truly missing entries at review time. In a multi-tenant production
        deployment we would persist a fallback journal locally; in this
        single-host demo, a log line is the honest answer.
        """
        try:
            self._col.insert_one(
                {
                    "user": user,
                    "action": action,
                    "target_collection": target_collection,
                    "target_id": target_id,
                    "timestamp": datetime.now(timezone.utc),
                    "before": _redact(before),
                    "after": _redact(after),
                }
            )
        except Exception:  # pragma: no cover - operational logging only
            logger.exception(
                "audit_log write failed for action=%s target=%s",
                action,
                target_id,
            )
