from __future__ import annotations

import sqlite3
from pathlib import Path

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
  FOREIGN KEY (team_id) REFERENCES teams(id),
  FOREIGN KEY (submission_period_id) REFERENCES submission_periods(id),
  FOREIGN KEY (ground_truth_version_id) REFERENCES ground_truth_versions(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_one_successful_submission
ON submissions(team_id, subtask, submission_period_id)
WHERE status IN ('accepted', 'evaluated', 'evaluation_failed');

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


def connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: Path) -> None:
    with connect(database_path) as connection:
        connection.executescript(SCHEMA)
        connection.executemany(
            """
            INSERT OR IGNORE INTO submission_periods (name, starts_at_jst, deadline_at_jst)
            VALUES (?, ?, ?)
            """,
            DEFAULT_PERIODS,
        )
        connection.commit()
