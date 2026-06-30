import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.accounts import create_organizer, create_team
from app.config import Settings
from app.db import connect, initialize_database
from app.main import create_app


def make_settings(tmp: str) -> Settings:
    root = Path(tmp)
    return Settings(
        app_name="Test Submission System",
        environment="test",
        database_path=root / "app.sqlite3",
        storage_root=root / "storage",
        secret_key="test-secret",
        max_upload_bytes=10 * 1024 * 1024,
    )


def seed_accounts(settings: Settings):
    initialize_database(settings.database_path)
    with connect(settings.database_path) as connection:
        organizer = create_organizer(
            connection,
            username="admin",
            display_name="Admin User",
        )
        team = create_team(
            connection,
            team_id="team-001",
            display_name="Team 001",
            subtasks={"A"},
            created_by_organizer_id=organizer.id,
        )
    return organizer, team


def login(client: TestClient, user_id: str, password: str) -> None:
    response = client.post(
        "/login",
        data={"user_id": user_id, "password": password},
        follow_redirects=True,
    )
    assert response.status_code == 200


def test_organizer_can_view_submission_periods_page():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        response = client.get("/admin/periods")

        assert response.status_code == 200
        assert "Submission Periods" in response.text
        assert "normal" in response.text
        assert "late" in response.text
        assert "2026-08-01 15:00:00" in response.text


def test_admin_dashboard_links_to_submission_periods_page():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        response = client.get("/admin")

        assert response.status_code == 200
        assert "/admin/periods" in response.text


def test_team_cannot_view_submission_periods_page():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        _organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.get("/admin/periods", follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == "/team"


def test_organizer_can_update_submission_period_deadline_and_override():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        response = client.post(
            "/admin/periods/normal",
            data={
                "starts_at_jst": "2026-07-01 00:00:00",
                "deadline_at_jst": "2026-08-02 12:30:00",
                "is_open_override": "on",
            },
        )

        assert response.status_code == 200
        assert "Submission period updated." in response.text
        assert "2026-08-02 12:30:00" in response.text

        with connect(settings.database_path) as connection:
            row = connection.execute(
                """
                SELECT starts_at_jst, deadline_at_jst, is_open_override
                FROM submission_periods
                WHERE name = 'normal'
                """
            ).fetchone()

        assert row["starts_at_jst"] == "2026-07-01 00:00:00"
        assert row["deadline_at_jst"] == "2026-08-02 12:30:00"
        assert row["is_open_override"] == 1


def test_team_dashboard_uses_configured_submission_period_deadlines():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        client.post(
            "/admin/periods/normal",
            data={
                "starts_at_jst": "",
                "deadline_at_jst": "2026-08-03 09:45:00",
                "is_open_override": "on",
            },
        )

        client.get("/logout")
        login(client, "team-001", team.password)

        response = client.get("/team")

        assert response.status_code == 200
        assert "2026-08-03 09:45:00 JST" in response.text
        assert "reopened" in response.text
        assert "August 1, 2026 at 15:00 JST" not in response.text


def test_organizer_can_clear_submission_period_start_and_override():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        response = client.post(
            "/admin/periods/late",
            data={
                "starts_at_jst": "",
                "deadline_at_jst": "2026-10-16 00:00:00",
            },
        )

        assert response.status_code == 200
        assert "Submission period updated." in response.text

        with connect(settings.database_path) as connection:
            row = connection.execute(
                """
                SELECT starts_at_jst, deadline_at_jst, is_open_override
                FROM submission_periods
                WHERE name = 'late'
                """
            ).fetchone()

        assert row["starts_at_jst"] is None
        assert row["deadline_at_jst"] == "2026-10-16 00:00:00"
        assert row["is_open_override"] == 0


def test_invalid_period_timestamp_shows_error_without_update():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        response = client.post(
            "/admin/periods/normal",
            data={
                "starts_at_jst": "",
                "deadline_at_jst": "August 1",
            },
        )

        assert response.status_code == 200
        assert "Use timestamp format YYYY-MM-DD HH:MM:SS." in response.text

        with connect(settings.database_path) as connection:
            row = connection.execute(
                """
                SELECT deadline_at_jst
                FROM submission_periods
                WHERE name = 'normal'
                """
            ).fetchone()

        assert row["deadline_at_jst"] == "2026-08-01 15:00:00"
