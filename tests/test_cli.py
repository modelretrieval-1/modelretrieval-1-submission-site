import tempfile
from pathlib import Path
from unittest.mock import patch

from app.cli import create_admin, migrate_database
from app.config import Settings
from app.db import connect


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


def test_create_admin_cli_helper_creates_organizer():
    with tempfile.TemporaryDirectory() as tmp:
        test_settings = make_settings(tmp)

        with patch("app.cli.settings", test_settings):
            exit_code = create_admin(username="admin", display_name="Admin User")

        assert exit_code == 0
        with connect(test_settings.database_path) as connection:
            row = connection.execute(
                "SELECT username, display_name FROM organizers WHERE username = ?",
                ("admin",),
            ).fetchone()

        assert row["username"] == "admin"
        assert row["display_name"] == "Admin User"


def test_create_admin_cli_helper_rejects_duplicate_username():
    with tempfile.TemporaryDirectory() as tmp:
        test_settings = make_settings(tmp)

        with patch("app.cli.settings", test_settings):
            assert create_admin(username="admin", display_name="Admin User") == 0
            assert create_admin(username="admin", display_name="Admin User") == 1


def test_migrate_database_cli_helper_applies_migrations():
    with tempfile.TemporaryDirectory() as tmp:
        test_settings = make_settings(tmp)

        with patch("app.cli.settings", test_settings):
            exit_code = migrate_database()

        assert exit_code == 0
        with connect(test_settings.database_path) as connection:
            revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()

        assert revision["version_num"] == "20260706_0002"
