from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Literal

from app.auth import generate_password, hash_password, verify_password

Subtask = Literal["A", "B"]
AccountRole = Literal["organizer", "team"]


@dataclass(frozen=True)
class GeneratedAccount:
    id: int
    user_id: str
    password: str


@dataclass(frozen=True)
class AuthenticatedAccount:
    role: AccountRole
    id: int
    user_id: str
    display_name: str


@dataclass(frozen=True)
class TeamSummary:
    id: int
    team_id: str
    display_name: str
    is_active: bool
    created_at: str
    last_login_at: str | None
    subtasks: tuple[Subtask, ...]


@dataclass(frozen=True)
class OrganizerSummary:
    id: int
    username: str
    display_name: str
    is_active: bool
    created_at: str
    last_login_at: str | None


def create_organizer(
    connection: sqlite3.Connection,
    *,
    username: str,
    display_name: str,
) -> GeneratedAccount:
    password = generate_password()
    cursor = connection.execute(
        """
        INSERT INTO organizers (username, password_hash, display_name)
        VALUES (?, ?, ?)
        """,
        (username, hash_password(password), display_name),
    )
    connection.commit()
    return GeneratedAccount(id=cursor.lastrowid, user_id=username, password=password)


def create_team(
    connection: sqlite3.Connection,
    *,
    team_id: str,
    display_name: str,
    subtasks: set[Subtask],
    created_by_organizer_id: int | None = None,
) -> GeneratedAccount:
    if not subtasks:
        raise ValueError("Team must be registered for at least one subtask.")

    invalid_subtasks = subtasks - {"A", "B"}
    if invalid_subtasks:
        raise ValueError(f"Invalid subtasks: {', '.join(sorted(invalid_subtasks))}")

    password = generate_password()
    cursor = connection.execute(
        """
        INSERT INTO teams (team_id, password_hash, display_name, created_by_organizer_id)
        VALUES (?, ?, ?, ?)
        """,
        (team_id, hash_password(password), display_name, created_by_organizer_id),
    )
    internal_team_id = cursor.lastrowid
    connection.executemany(
        """
        INSERT INTO team_subtasks (team_id, subtask)
        VALUES (?, ?)
        """,
        [(internal_team_id, subtask) for subtask in sorted(subtasks)],
    )
    connection.commit()
    return GeneratedAccount(id=internal_team_id, user_id=team_id, password=password)


def authenticate(
    connection: sqlite3.Connection,
    user_id: str,
    password: str,
) -> AuthenticatedAccount | None:
    organizer = connection.execute(
        """
        SELECT id, username, password_hash, display_name
        FROM organizers
        WHERE username = ? AND is_active = 1
        """,
        (user_id,),
    ).fetchone()
    if organizer and verify_password(password, organizer["password_hash"]):
        connection.execute(
            "UPDATE organizers SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?",
            (organizer["id"],),
        )
        connection.commit()
        return AuthenticatedAccount(
            role="organizer",
            id=organizer["id"],
            user_id=organizer["username"],
            display_name=organizer["display_name"],
        )

    team = connection.execute(
        """
        SELECT id, team_id, password_hash, display_name
        FROM teams
        WHERE team_id = ? AND is_active = 1
        """,
        (user_id,),
    ).fetchone()
    if team and verify_password(password, team["password_hash"]):
        connection.execute(
            "UPDATE teams SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?",
            (team["id"],),
        )
        connection.commit()
        return AuthenticatedAccount(
            role="team",
            id=team["id"],
            user_id=team["team_id"],
            display_name=team["display_name"],
        )

    return None


def get_organizer_account(
    connection: sqlite3.Connection,
    organizer_id: int,
) -> AuthenticatedAccount | None:
    row = connection.execute(
        """
        SELECT id, username, display_name
        FROM organizers
        WHERE id = ? AND is_active = 1
        """,
        (organizer_id,),
    ).fetchone()
    if row is None:
        return None
    return AuthenticatedAccount(
        role="organizer",
        id=row["id"],
        user_id=row["username"],
        display_name=row["display_name"],
    )


def get_team_account(
    connection: sqlite3.Connection,
    internal_team_id: int,
) -> AuthenticatedAccount | None:
    row = connection.execute(
        """
        SELECT id, team_id, display_name
        FROM teams
        WHERE id = ? AND is_active = 1
        """,
        (internal_team_id,),
    ).fetchone()
    if row is None:
        return None
    return AuthenticatedAccount(
        role="team",
        id=row["id"],
        user_id=row["team_id"],
        display_name=row["display_name"],
    )


def get_team_subtasks(connection: sqlite3.Connection, internal_team_id: int) -> set[Subtask]:
    rows = connection.execute(
        """
        SELECT subtask
        FROM team_subtasks
        WHERE team_id = ?
        ORDER BY subtask
        """,
        (internal_team_id,),
    ).fetchall()
    return {row["subtask"] for row in rows}


def list_teams(connection: sqlite3.Connection) -> list[TeamSummary]:
    rows = connection.execute(
        """
        SELECT
          teams.id,
          teams.team_id,
          teams.display_name,
          teams.is_active,
          teams.created_at,
          teams.last_login_at,
          GROUP_CONCAT(team_subtasks.subtask, ',') AS subtasks
        FROM teams
        LEFT JOIN team_subtasks ON team_subtasks.team_id = teams.id
        GROUP BY teams.id
        ORDER BY teams.team_id
        """
    ).fetchall()
    return [
        TeamSummary(
            id=row["id"],
            team_id=row["team_id"],
            display_name=row["display_name"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            last_login_at=row["last_login_at"],
            subtasks=tuple(sorted(row["subtasks"].split(","))) if row["subtasks"] else (),
        )
        for row in rows
    ]


def list_organizers(connection: sqlite3.Connection) -> list[OrganizerSummary]:
    rows = connection.execute(
        """
        SELECT id, username, display_name, is_active, created_at, last_login_at
        FROM organizers
        ORDER BY username
        """
    ).fetchall()
    return [
        OrganizerSummary(
            id=row["id"],
            username=row["username"],
            display_name=row["display_name"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            last_login_at=row["last_login_at"],
        )
        for row in rows
    ]


def team_can_submit(
    connection: sqlite3.Connection,
    internal_team_id: int,
    subtask: Subtask,
) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM team_subtasks
        WHERE team_id = ? AND subtask = ?
        """,
        (internal_team_id, subtask),
    ).fetchone()
    return row is not None


def reset_team_password(connection: sqlite3.Connection, internal_team_id: int) -> str:
    password = generate_password()
    connection.execute(
        """
        UPDATE teams
        SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (hash_password(password), internal_team_id),
    )
    connection.commit()
    return password


def reset_team_password_by_team_id(connection: sqlite3.Connection, team_id: str) -> str | None:
    row = connection.execute(
        """
        SELECT id
        FROM teams
        WHERE team_id = ?
        """,
        (team_id,),
    ).fetchone()
    if row is None:
        return None
    return reset_team_password(connection, row["id"])


def reset_organizer_password(connection: sqlite3.Connection, organizer_id: int) -> str:
    password = generate_password()
    connection.execute(
        """
        UPDATE organizers
        SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (hash_password(password), organizer_id),
    )
    connection.commit()
    return password


def reset_organizer_password_by_username(
    connection: sqlite3.Connection,
    username: str,
) -> str | None:
    row = connection.execute(
        """
        SELECT id
        FROM organizers
        WHERE username = ?
        """,
        (username,),
    ).fetchone()
    if row is None:
        return None
    return reset_organizer_password(connection, row["id"])


def change_organizer_password(
    connection: sqlite3.Connection,
    *,
    organizer_id: int,
    current_password: str,
    new_password: str,
) -> bool:
    row = connection.execute(
        """
        SELECT password_hash
        FROM organizers
        WHERE id = ? AND is_active = 1
        """,
        (organizer_id,),
    ).fetchone()
    if row is None or not verify_password(current_password, row["password_hash"]):
        return False

    connection.execute(
        """
        UPDATE organizers
        SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (hash_password(new_password), organizer_id),
    )
    connection.commit()
    return True
