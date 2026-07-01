import re
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


def generated_password(response_text: str) -> str:
    match = re.search(r"<code>([^<]+)</code>", response_text)
    assert match is not None
    return match.group(1)


def test_organizer_can_view_teams_page():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        response = client.get("/admin/teams")

        assert response.status_code == 200
        assert (
            "Register participant teams, assign eligible subtasks, and rotate team passwords."
            in response.text
        )
        assert "Registered Teams" in response.text
        assert "Showing 1 team." in response.text
        assert "team-001" in response.text
        assert "Subtask A" in response.text


def test_team_cannot_view_teams_page():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        _organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "team-001", team.password)

        response = client.get("/admin/teams", follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == "/team"


def test_organizer_can_add_team_with_subtask_a():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        response = client.post(
            "/admin/teams",
            data={
                "team_id": "team-002",
                "display_name": "Team 002",
                "subtasks": "A",
            },
        )

        assert response.status_code == 200
        assert "Generated Password" in response.text
        assert "team-002" in response.text
        assert "Team 002" in response.text
        assert "Subtask A" in response.text

        password = generated_password(response.text)
        with connect(settings.database_path) as connection:
            account = authenticate(connection, "team-002", password)

        assert account is not None
        assert account.role == "team"


def test_organizer_can_add_team_with_both_subtasks():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        response = client.post(
            "/admin/teams",
            data={
                "team_id": "team-003",
                "display_name": "Team 003",
                "subtasks": ["A", "B"],
            },
        )

        assert response.status_code == 200
        assert "team-003" in response.text
        assert "Subtask A" in response.text
        assert "Subtask B" in response.text


def test_duplicate_team_id_shows_error():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, _team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        response = client.post(
            "/admin/teams",
            data={
                "team_id": "team-001",
                "display_name": "Duplicate Team",
                "subtasks": "A",
            },
        )

        assert response.status_code == 200
        assert "Could not create team" in response.text


def test_regenerated_password_invalidates_old_password():
    with tempfile.TemporaryDirectory() as tmp:
        settings = make_settings(tmp)
        organizer, team = seed_accounts(settings)
        client = TestClient(create_app(settings))
        login(client, "admin", organizer.password)

        response = client.post("/admin/teams/team-001/password")

        assert response.status_code == 200
        assert "Generated Password" in response.text

        new_password = generated_password(response.text)
        with connect(settings.database_path) as connection:
            assert authenticate(connection, "team-001", team.password) is None
            assert authenticate(connection, "team-001", new_password) is not None
