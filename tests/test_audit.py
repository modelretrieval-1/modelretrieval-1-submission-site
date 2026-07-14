import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.accounts import create_organizer
from app.audit import record_audit_event
from app.config import Settings
from app.db import connect, initialize_database
from app.main import create_app


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


def test_authentication_events_are_recorded_without_passwords():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        settings = Settings(
            app_name="Audit Test",
            environment="test",
            database_path=root / "app.sqlite3",
            storage_root=root / "storage",
            secret_key="test-secret",
            max_upload_bytes=50 * 1024 * 1024,
        )
        initialize_database(settings.database_path)
        with connect(settings.database_path) as connection:
            organizer = create_organizer(
                connection, username="admin", display_name="Admin User"
            )
        client = TestClient(create_app(settings))
        client.post("/login", data={"user_id": "admin", "password": "wrong"})
        client.post("/login", data={"user_id": "admin", "password": organizer.password})
        client.get("/logout")

        with connect(settings.database_path) as connection:
            rows = connection.execute(
                "SELECT event_type, actor_id, metadata_json FROM audit_events ORDER BY id"
            ).fetchall()
        assert [row["event_type"] for row in rows] == [
            "login_failed",
            "login_succeeded",
            "logout",
        ]
        assert all(organizer.password not in (row["metadata_json"] or "") for row in rows)
