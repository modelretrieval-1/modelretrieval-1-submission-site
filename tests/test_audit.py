import json

from app.audit import record_audit_event
from app.db import connect, initialize_database


def test_record_audit_event_serializes_structured_metadata(tmp_path):
    database_path = tmp_path / "audit.sqlite3"
    initialize_database(database_path)

    with connect(database_path) as connection:
        record_audit_event(
            connection,
            actor_type="anonymous",
            actor_id=None,
            event_type="login_failed",
            entity_type="account",
            metadata={"reason": "invalid_credentials", "user_id": "admin"},
        )

    with connect(database_path) as connection:
        row = connection.execute("SELECT * FROM audit_events").fetchone()
    assert row["actor_type"] == "anonymous"
    assert row["actor_id"] is None
    assert row["event_type"] == "login_failed"
    assert json.loads(row["metadata_json"]) == {
        "reason": "invalid_credentials",
        "user_id": "admin",
    }
    assert "+09:00" in row["created_at_jst"]

