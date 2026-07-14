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


def list_audit_events(
    connection: sqlite3.Connection,
    *,
    event_type: str = "",
    actor_type: str = "",
    entity_type: str = "",
    entity_id: str = "",
    date_from: str = "",
    date_to: str = "",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[sqlite3.Row], int]:
    clauses: list[str] = []
    params: list[object] = []
    filters = (("event_type", event_type), ("actor_type", actor_type), ("entity_type", entity_type))
    for column, value in filters:
        if value:
            clauses.append(f"{column} = ?")
            params.append(value)
    if entity_id:
        clauses.append("CAST(entity_id AS TEXT) = ?")
        params.append(entity_id)
    if date_from:
        clauses.append("created_at_jst >= ?")
        params.append(f"{date_from} 00:00:00")
    if date_to:
        clauses.append("created_at_jst <= ?")
        params.append(f"{date_to} 23:59:59")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    total = connection.execute(f"SELECT COUNT(*) FROM audit_events {where}", params).fetchone()[0]
    offset = max(page - 1, 0) * page_size
    rows = connection.execute(
        f"SELECT * FROM audit_events {where} ORDER BY created_at_jst DESC, id DESC "
        "LIMIT ? OFFSET ?",
        [*params, page_size, offset],
    ).fetchall()
    return rows, total
