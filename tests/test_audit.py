import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.accounts import create_organizer
from app.audit import list_audit_events, record_audit_event
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


def test_list_audit_events_filters_and_paginates(tmp_path):
    database_path = tmp_path / "audit.sqlite3"
    initialize_database(database_path)
    with connect(database_path) as connection:
        for index in range(3):
            record_audit_event(
                connection,
                actor_type="system" if index == 2 else "organizer",
                actor_id=1,
                event_type=f"event_{index}",
                entity_type="submission",
            )
        rows, total = list_audit_events(
            connection, actor_type="organizer", page=1, page_size=1
        )
    assert total == 2
    assert len(rows) == 1


def test_audit_page_formats_timestamps_and_filters_full_jst_days(tmp_path):
    settings = Settings(
        app_name="Audit Test",
        environment="test",
        database_path=tmp_path / "app.sqlite3",
        storage_root=tmp_path / "storage",
        secret_key="test-secret",
        max_upload_bytes=50 * 1024 * 1024,
    )
    initialize_database(settings.database_path)
    timestamps = {
        "previous_day": "2026-10-13 23:59:59+09:00",
        "day_start": "2026-10-14 00:00:00+09:00",
        "during_day": "2026-10-14 23:20:24+09:00",
        "day_end": "2026-10-14 23:59:59+09:00",
        "next_day": "2026-10-15 00:00:00+09:00",
    }
    with connect(settings.database_path) as connection:
        organizer = create_organizer(connection, username="admin", display_name="Admin User")
        connection.executemany(
            "INSERT INTO audit_events (actor_type, event_type, created_at_jst) "
            "VALUES ('system', ?, ?)",
            timestamps.items(),
        )

    client = TestClient(create_app(settings))
    client.post("/login", data={"user_id": "admin", "password": organizer.password})
    response = client.get("/admin/audit-events")
    assert response.status_code == 200
    assert "2026-10-14 23:20:24 JST" in response.text
    assert "+09:00" not in response.text

    for filters, expected_events in (
        ({"date_from": "2026-10-14"}, set(timestamps) - {"previous_day"}),
        ({"date_to": "2026-10-14"}, set(timestamps) - {"next_day"}),
        (
            {"date_from": "2026-10-14", "date_to": "2026-10-14"},
            {"day_start", "during_day", "day_end"},
        ),
    ):
        response = client.get("/admin/audit-events", params=filters)
        assert response.status_code == 200
        for event_type in timestamps:
            is_rendered = f"<code>{event_type}</code>" in response.text
            assert is_rendered == (event_type in expected_events)
        assert "+09:00" not in response.text

    with connect(settings.database_path) as connection:
        stored = dict(
            connection.execute(
                "SELECT event_type, created_at_jst FROM audit_events WHERE actor_type = 'system'"
            ).fetchall()
        )
    assert stored == timestamps
