import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.db import initialize_database


class DatabaseTests(unittest.TestCase):
    def test_initialize_database_creates_tables_and_default_periods(self):
        with tempfile.TemporaryDirectory() as tmp:
            database_path = Path(tmp) / "app.sqlite3"

            initialize_database(database_path)

            with sqlite3.connect(database_path) as connection:
                table_rows = connection.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type = 'table'
                    ORDER BY name
                    """
                ).fetchall()
                table_names = {row[0] for row in table_rows}

                self.assertIn("teams", table_names)
                self.assertIn("submissions", table_names)
                self.assertIn("evaluation_results", table_names)

                periods = connection.execute(
                    "SELECT name, deadline_at_jst FROM submission_periods ORDER BY name"
                ).fetchall()

            self.assertEqual(
                periods,
                [
                    ("late", "2026-10-15 23:59:00"),
                    ("normal", "2026-08-01 15:00:00"),
                ],
            )

    def test_initialize_database_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            database_path = Path(tmp) / "app.sqlite3"

            initialize_database(database_path)
            initialize_database(database_path)

            with sqlite3.connect(database_path) as connection:
                count = connection.execute("SELECT COUNT(*) FROM submission_periods").fetchone()[0]

            self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()

