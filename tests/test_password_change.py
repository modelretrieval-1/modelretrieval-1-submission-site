import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.accounts import authenticate, create_organizer, create_team
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


def login(client: TestClient, user_id: str, password: str) -> None:
    response = client.post(
        "/login",
        data={"user_id": user_id, "password": password},
        follow_redirects=True,
    )
    assert response.status_code == 200


def test_organizer_can_view_password_change_page():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        response = client.get("/account/password")

        assert response.status_code == 200
        assert "Change Password" in response.text
        assert "Rotate the password for Admin User (admin)." in response.text
        assert "Password Details" in response.text
        assert "Current Password" in response.text


def test_team_can_view_password_change_page():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        _organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.get("/account/password")

        assert response.status_code == 200
        assert "Change Password" in response.text
        assert "Password Details" in response.text
        assert "Team 001" in response.text


def test_incorrect_current_password_shows_error():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        response = client.post(
            "/account/password",
            data={
                "current_password": "wrong",
                "new_password": "new-secret",
                "confirm_password": "new-secret",
            },
        )

        assert response.status_code == 200
        assert "Current password is incorrect." in response.text


def test_mismatched_confirmation_shows_error():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        response = client.post(
            "/account/password",
            data={
                "current_password": organizer.password,
                "new_password": "new-secret",
                "confirm_password": "different-secret",
            },
        )

        assert response.status_code == 200
        assert "New password and confirmation do not match." in response.text


def test_successful_password_change_invalidates_old_password():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        response = client.post(
            "/account/password",
            data={
                "current_password": organizer.password,
                "new_password": "new-secret",
                "confirm_password": "new-secret",
            },
        )

        assert response.status_code == 200
        assert "Password changed." in response.text

        with connect(settings.database_path) as connection:
            assert authenticate(connection, "admin", organizer.password) is None
            assert authenticate(connection, "admin", "new-secret") is not None


def test_successful_team_password_change_invalidates_old_password_and_keeps_session():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        _organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.post(
            "/account/password",
            data={
                "current_password": team.password,
                "new_password": "new-team-secret",
                "confirm_password": "new-team-secret",
            },
        )

        assert response.status_code == 200
        assert "Password changed." in response.text

        dashboard_response = client.get("/team")
        assert dashboard_response.status_code == 200
        assert "Team Dashboard" in dashboard_response.text

        with connect(settings.database_path) as connection:
            assert authenticate(connection, "team-001", team.password) is None
            assert authenticate(connection, "team-001", "new-team-secret") is not None
