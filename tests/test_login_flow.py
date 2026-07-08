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
        max_upload_bytes=50 * 1024 * 1024,
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


def test_team_login_redirects_to_team_dashboard():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        _organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))

        response = client.post(
            "/login",
            data={"user_id": "team-001", "password": team.password},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert "Team Dashboard" in response.text
        assert "Subtask A" in response.text


def test_organizer_login_redirects_to_admin_dashboard():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))

        response = client.post(
            "/login",
            data={"user_id": "admin", "password": organizer.password},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert "Organizer Dashboard" in response.text


def test_invalid_login_shows_error():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        seed_accounts(settings)
        client = TestClient(create_app(settings))

        response = client.post(
            "/login",
            data={"user_id": "admin", "password": "wrong"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert "Invalid user ID or password." in response.text


def test_team_cannot_access_admin_dashboard():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        _organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        client.post(
            "/login",
            data={"user_id": "team-001", "password": team.password},
            follow_redirects=True,
        )

        response = client.get("/admin", follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == "/team"


def test_logout_clears_access():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        _organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        client.post(
            "/login",
            data={"user_id": "team-001", "password": team.password},
            follow_redirects=True,
        )

        client.get("/logout", follow_redirects=True)
        response = client.get("/team", follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == "/login"
