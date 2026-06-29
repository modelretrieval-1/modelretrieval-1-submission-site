import tempfile
from pathlib import Path

from app.accounts import (
    authenticate,
    change_organizer_password,
    create_organizer,
    create_team,
    get_team_subtasks,
    reset_team_password,
    team_can_submit,
)
from app.db import connect, initialize_database


def initialized_connection():
    tmp = tempfile.TemporaryDirectory()
    database_path = Path(tmp.name) / "app.sqlite3"
    initialize_database(database_path)
    connection = connect(database_path)
    return tmp, connection


def test_create_organizer_and_authenticate():
    tmp, connection = initialized_connection()
    with tmp, connection:
        organizer = create_organizer(
            connection,
            username="admin",
            display_name="Admin User",
        )

        account = authenticate(connection, "admin", organizer.password)

        assert account is not None
        assert account.role == "organizer"
        assert account.user_id == "admin"
        assert account.display_name == "Admin User"


def test_create_team_with_subtasks_and_authenticate():
    tmp, connection = initialized_connection()
    with tmp, connection:
        organizer = create_organizer(
            connection,
            username="admin",
            display_name="Admin User",
        )
        team = create_team(
            connection,
            team_id="team-001",
            display_name="Team 001",
            subtasks={"A", "B"},
            created_by_organizer_id=organizer.id,
        )

        account = authenticate(connection, "team-001", team.password)

        assert account is not None
        assert account.role == "team"
        assert get_team_subtasks(connection, team.id) == {"A", "B"}
        assert team_can_submit(connection, team.id, "A")
        assert team_can_submit(connection, team.id, "B")


def test_team_subtask_eligibility_blocks_unregistered_subtask():
    tmp, connection = initialized_connection()
    with tmp, connection:
        team = create_team(
            connection,
            team_id="team-002",
            display_name="Team 002",
            subtasks={"A"},
        )

        assert team_can_submit(connection, team.id, "A")
        assert not team_can_submit(connection, team.id, "B")


def test_authenticate_rejects_wrong_password():
    tmp, connection = initialized_connection()
    with tmp, connection:
        create_organizer(connection, username="admin", display_name="Admin User")

        account = authenticate(connection, "admin", "wrong")

        assert account is None


def test_reset_team_password_invalidates_old_password():
    tmp, connection = initialized_connection()
    with tmp, connection:
        team = create_team(
            connection,
            team_id="team-003",
            display_name="Team 003",
            subtasks={"B"},
        )
        new_password = reset_team_password(connection, team.id)

        assert authenticate(connection, "team-003", team.password) is None
        assert authenticate(connection, "team-003", new_password) is not None


def test_change_organizer_password_requires_current_password():
    tmp, connection = initialized_connection()
    with tmp, connection:
        organizer = create_organizer(connection, username="admin", display_name="Admin User")

        assert not change_organizer_password(
            connection,
            organizer_id=organizer.id,
            current_password="wrong",
            new_password="new-secret",
        )
        assert change_organizer_password(
            connection,
            organizer_id=organizer.id,
            current_password=organizer.password,
            new_password="new-secret",
        )
        assert authenticate(connection, "admin", organizer.password) is None
        assert authenticate(connection, "admin", "new-secret") is not None

