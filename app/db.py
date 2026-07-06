from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS organizers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  display_name TEXT NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS teams (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  team_id TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  display_name TEXT NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_by_organizer_id INTEGER,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_login_at TEXT,
  FOREIGN KEY (created_by_organizer_id) REFERENCES organizers(id)
);

CREATE TABLE IF NOT EXISTS team_subtasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  team_id INTEGER NOT NULL,
  subtask TEXT NOT NULL CHECK (subtask IN ('A', 'B')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (team_id, subtask),
  FOREIGN KEY (team_id) REFERENCES teams(id)
);

CREATE TABLE IF NOT EXISTS submission_periods (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  starts_at_jst TEXT,
  deadline_at_jst TEXT NOT NULL,
  is_open_override INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ground_truth_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  subtask TEXT NOT NULL CHECK (subtask IN ('A', 'B')),
  version_label TEXT NOT NULL,
  stored_file_path TEXT NOT NULL,
  file_sha256 TEXT NOT NULL,
  uploaded_by_organizer_id INTEGER NOT NULL,
  uploaded_at_jst TEXT NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 0,
  validation_status TEXT NOT NULL,
  notes TEXT,
  FOREIGN KEY (uploaded_by_organizer_id) REFERENCES organizers(id)
);

CREATE TABLE IF NOT EXISTS submissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  team_id INTEGER NOT NULL,
  subtask TEXT NOT NULL CHECK (subtask IN ('A', 'B')),
  submission_period_id INTEGER NOT NULL,
  status TEXT NOT NULL,
  original_filename TEXT NOT NULL,
  stored_file_path TEXT,
  file_sha256 TEXT,
  file_size_bytes INTEGER NOT NULL DEFAULT 0,
  submitted_at_jst TEXT NOT NULL,
  validation_summary TEXT,
  ground_truth_version_id INTEGER,
  is_current INTEGER NOT NULL DEFAULT 0,
  superseded_at_jst TEXT,
  superseded_by_submission_id INTEGER,
  superseded_reason TEXT,
  superseded_by_organizer_id INTEGER,
  FOREIGN KEY (team_id) REFERENCES teams(id),
  FOREIGN KEY (submission_period_id) REFERENCES submission_periods(id),
  FOREIGN KEY (ground_truth_version_id) REFERENCES ground_truth_versions(id),
  FOREIGN KEY (superseded_by_submission_id) REFERENCES submissions(id),
  FOREIGN KEY (superseded_by_organizer_id) REFERENCES organizers(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_one_current_successful_submission
ON submissions(team_id, subtask, submission_period_id)
WHERE status IN ('accepted', 'evaluated', 'evaluation_failed') AND is_current = 1;

CREATE TABLE IF NOT EXISTS resubmission_permissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  team_id INTEGER NOT NULL,
  subtask TEXT NOT NULL CHECK (subtask IN ('A', 'B')),
  submission_period_id INTEGER NOT NULL,
  granted_by_organizer_id INTEGER NOT NULL,
  granted_at_jst TEXT NOT NULL,
  reason TEXT,
  used_by_submission_id INTEGER,
  used_at_jst TEXT,
  is_used INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (team_id) REFERENCES teams(id),
  FOREIGN KEY (submission_period_id) REFERENCES submission_periods(id),
  FOREIGN KEY (granted_by_organizer_id) REFERENCES organizers(id),
  FOREIGN KEY (used_by_submission_id) REFERENCES submissions(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_unused_resubmission_permission
ON resubmission_permissions(team_id, subtask, submission_period_id)
WHERE is_used = 0;

CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  submission_id INTEGER NOT NULL,
  run_id TEXT NOT NULL,
  line_count INTEGER NOT NULL DEFAULT 0,
  query_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (submission_id, run_id),
  FOREIGN KEY (submission_id) REFERENCES submissions(id)
);

CREATE TABLE IF NOT EXISTS validation_errors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  submission_id INTEGER NOT NULL,
  line_number INTEGER,
  field_name TEXT,
  error_code TEXT NOT NULL,
  message TEXT NOT NULL,
  severity TEXT NOT NULL DEFAULT 'error',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (submission_id) REFERENCES submissions(id)
);

CREATE TABLE IF NOT EXISTS evaluation_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  submission_id INTEGER NOT NULL,
  run_id INTEGER NOT NULL,
  ground_truth_version_id INTEGER NOT NULL,
  metric_name TEXT NOT NULL,
  metric_value REAL NOT NULL,
  created_at_jst TEXT NOT NULL,
  FOREIGN KEY (submission_id) REFERENCES submissions(id),
  FOREIGN KEY (run_id) REFERENCES runs(id),
  FOREIGN KEY (ground_truth_version_id) REFERENCES ground_truth_versions(id)
);

CREATE TABLE IF NOT EXISTS evaluation_query_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  submission_id INTEGER NOT NULL,
  run_id INTEGER NOT NULL,
  ground_truth_version_id INTEGER NOT NULL,
  topic_id TEXT NOT NULL,
  metric_name TEXT NOT NULL,
  metric_value REAL NOT NULL,
  created_at_jst TEXT NOT NULL,
  FOREIGN KEY (submission_id) REFERENCES submissions(id),
  FOREIGN KEY (run_id) REFERENCES runs(id),
  FOREIGN KEY (ground_truth_version_id) REFERENCES ground_truth_versions(id)
);

CREATE TABLE IF NOT EXISTS audit_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor_type TEXT NOT NULL,
  actor_id INTEGER,
  event_type TEXT NOT NULL,
  entity_type TEXT,
  entity_id INTEGER,
  metadata_json TEXT,
  created_at_jst TEXT NOT NULL
);
"""


DEFAULT_PERIODS = [
    ("normal", None, "2026-08-01 15:00:00"),
    ("late", None, "2026-10-15 23:59:00"),
]

EXPECTED_BASELINE_TABLES = {
    "audit_events",
    "evaluation_query_results",
    "evaluation_results",
    "ground_truth_versions",
    "organizers",
    "runs",
    "submission_periods",
    "submissions",
    "team_subtasks",
    "teams",
    "validation_errors",
}


def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def alembic_config(database_path: Path) -> Config:
    project_root = Path(__file__).resolve().parent.parent
    config = Config(str(project_root / "alembic.ini"))
    config.attributes["database_path"] = database_path
    return config


def _table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        """
        SELECT name FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        """
    ).fetchall()
    return {row[0] for row in rows}


def _current_revision(connection: sqlite3.Connection) -> str | None:
    table_names = _table_names(connection)
    if "alembic_version" not in table_names:
        return None
    row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    if row is None:
        return None
    return row[0]


def _column_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _schema_revision_for_unversioned_database(
    connection: sqlite3.Connection,
    config: Config,
) -> str:
    table_names = _table_names(connection)
    submission_columns = _column_names(connection, "submissions")
    if "resubmission_permissions" in table_names and "is_current" in submission_columns:
        return _head_revision(config)
    return "20260706_0001"


def _head_revision(config: Config) -> str:
    script = ScriptDirectory.from_config(config)
    return script.get_current_head()


def _stamp_existing_baseline_if_needed(database_path: Path, config: Config) -> None:
    with connect(database_path) as connection:
        table_names = _table_names(connection)
        if not table_names:
            return

        missing_tables = EXPECTED_BASELINE_TABLES - table_names
        if missing_tables:
            missing = ", ".join(sorted(missing_tables))
            raise RuntimeError(
                "Existing database is not managed by Alembic and does not match the "
                f"baseline schema. Missing tables: {missing}."
            )

        current_revision = _current_revision(connection)
        if current_revision is not None:
            return
        stamp_revision = _schema_revision_for_unversioned_database(connection, config)

    command.stamp(config, stamp_revision, purge=True)


def run_migrations(database_path: Path) -> None:
    config = alembic_config(database_path)
    _stamp_existing_baseline_if_needed(database_path, config)
    command.upgrade(config, "head")


def verify_database_current(database_path: Path) -> None:
    config = alembic_config(database_path)
    head_revision = _head_revision(config)

    with connect(database_path) as connection:
        current_revision = _current_revision(connection)

    if current_revision != head_revision:
        raise RuntimeError(
            "Database schema is not at the expected Alembic revision. "
            f"Current revision: {current_revision or 'none'}; expected: {head_revision}."
        )


def initialize_database(database_path: Path) -> None:
    run_migrations(database_path)
