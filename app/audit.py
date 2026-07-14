"""Append-only audit event helpers."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")


def record_audit_event(
    connection: sqlite3.Connection,
    *,
    actor_type: str,
    actor_id: int | None,
    event_type: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    metadata: dict | None = None,
) -> None:
    """Append one structured audit event to the current transaction."""
    metadata_json = (
        json.dumps(metadata, sort_keys=True, separators=(",", ":")) if metadata else None
    )
    created_at_jst = datetime.now(JST).replace(microsecond=0).isoformat(sep=" ")
    connection.execute(
        """
        INSERT INTO audit_events
          (actor_type, actor_id, event_type, entity_type, entity_id, metadata_json, created_at_jst)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (actor_type, actor_id, event_type, entity_type, entity_id, metadata_json, created_at_jst),
    )
