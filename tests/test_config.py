import os
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config import load_settings


class SettingsTests(unittest.TestCase):
    def test_load_settings_uses_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = load_settings()

        self.assertEqual(settings.environment, "development")
        self.assertEqual(settings.max_upload_bytes, 10 * 1024 * 1024)
        self.assertTrue(settings.database_path.name.endswith(".sqlite3"))
        self.assertEqual(settings.submissions_dir, settings.storage_root / "submissions")

    def test_load_settings_reads_environment(self):
        env = {
            "APP_NAME": "Test App",
            "APP_ENV": "test",
            "DATABASE_PATH": "/tmp/test-app.sqlite3",
            "STORAGE_ROOT": "/tmp/test-storage",
            "SECRET_KEY": "secret",
            "MAX_UPLOAD_BYTES": "123",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = load_settings()

        self.assertEqual(settings.app_name, "Test App")
        self.assertEqual(settings.environment, "test")
        self.assertEqual(settings.database_path, Path("/tmp/test-app.sqlite3"))
        self.assertEqual(settings.storage_root, Path("/tmp/test-storage"))
        self.assertEqual(settings.secret_key, "secret")
        self.assertEqual(settings.max_upload_bytes, 123)


if __name__ == "__main__":
    unittest.main()

