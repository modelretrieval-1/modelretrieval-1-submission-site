import tempfile
import unittest
from pathlib import Path

from alembic import command

from app.db import (
    SCHEMA,
    alembic_config,
    connect,
    initialize_database,
    run_migrations,
    verify_database_current,
)


class DatabaseTests(unittest.TestCase):
    def test_initialize_database_creates_tables_and_default_periods(self):
        with tempfile.TemporaryDirectory() as tmp:
            database_path = Path(tmp) / "app.sqlite3"

            initialize_database(database_path)

            with connect(database_path) as connection:
                table_rows = connection.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type = 'table'
                    ORDER BY name
                    """
                ).fetchall()
                table_names = {row["name"] for row in table_rows}

                self.assertIn("teams", table_names)
                self.assertIn("submissions", table_names)
                self.assertIn("evaluation_results", table_names)
                self.assertIn("evaluation_query_results", table_names)
                self.assertIn("resubmission_permissions", table_names)
                self.assertIn("alembic_version", table_names)

                period_rows = connection.execute(
                    "SELECT name, deadline_at_jst FROM submission_periods ORDER BY name"
                ).fetchall()
                periods = [(row["name"], row["deadline_at_jst"]) for row in period_rows]
                revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()

            self.assertEqual(
                periods,
                [
                    ("late", "2026-10-15 23:59:00"),
                    ("normal", "2026-08-01 15:00:00"),
                ],
            )
            self.assertEqual(revision[0], "20260708_0003")
            verify_database_current(database_path)

    def test_initialize_database_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            database_path = Path(tmp) / "app.sqlite3"

            initialize_database(database_path)
            initialize_database(database_path)

            with connect(database_path) as connection:
                count = connection.execute("SELECT COUNT(*) FROM submission_periods").fetchone()[0]

            self.assertEqual(count, 2)

    def test_successful_submission_partial_unique_index_is_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            database_path = Path(tmp) / "app.sqlite3"

            initialize_database(database_path)

            with connect(database_path) as connection:
                indexes = connection.execute("PRAGMA index_list(submissions)").fetchall()
                index_names = {row["name"] for row in indexes}

                self.assertIn("idx_one_current_successful_submission", index_names)

                index_sql = connection.execute(
                    """
                    SELECT sql FROM sqlite_master
                    WHERE type = 'index' AND name = 'idx_one_current_successful_submission'
                    """
                ).fetchone()["sql"]

            self.assertIn(
                "WHERE status IN ('accepted', 'queued', 'processing', 'evaluated', "
                "'evaluation_failed')",
                index_sql,
            )
            self.assertIn("is_current = 1", index_sql)

    def test_migrations_stamp_legacy_baseline_database_with_empty_version_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            database_path = Path(tmp) / "app.sqlite3"
            config = alembic_config(database_path)

            command.upgrade(config, "20260706_0001")
            with connect(database_path) as connection:
                connection.execute("DELETE FROM alembic_version")
                connection.commit()

            run_migrations(database_path)

            with connect(database_path) as connection:
                revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()
                permissions_table = connection.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type = 'table' AND name = 'resubmission_permissions'
                    """
                ).fetchone()

            self.assertEqual(revision["version_num"], "20260708_0003")
            self.assertIsNotNone(permissions_table)

    def test_migrations_stamp_unversioned_current_schema_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            database_path = Path(tmp) / "app.sqlite3"

            with connect(database_path) as connection:
                connection.executescript(SCHEMA)
                connection.commit()

            run_migrations(database_path)

            with connect(database_path) as connection:
                revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()

            self.assertEqual(revision["version_num"], "20260708_0003")


if __name__ == "__main__":
    unittest.main()
