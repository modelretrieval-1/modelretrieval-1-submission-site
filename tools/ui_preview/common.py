"""Paths and settings shared by the standalone preview commands."""

from pathlib import Path

from app.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = REPO_ROOT / ".ui-preview"
PASSWORD = "demo-password-123"


def preview_settings(root: Path) -> Settings:
    return Settings(
        app_name="NTCIR-19 ModelRetrieval Submissions",
        environment="development",
        database_path=root / "app.sqlite3",
        storage_root=root / "storage",
        secret_key="ui-preview-local-demo-secret-do-not-use-in-production",
        max_upload_bytes=500 * 1024 * 1024,
        # No background worker or orphan recovery; eager uploads process only
        # their own submission ID, never the existing demo queue.
        evaluation_mode="eager",
    )
