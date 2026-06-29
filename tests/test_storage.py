import tempfile
import unittest
from pathlib import Path

from app.config import Settings
from app.storage import ensure_storage


class StorageTests(unittest.TestCase):
    def test_ensure_storage_creates_required_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "storage"
            settings = Settings(
                app_name="Test",
                environment="test",
                database_path=Path(tmp) / "app.sqlite3",
                storage_root=root,
                secret_key="secret",
                max_upload_bytes=10,
            )

            paths = ensure_storage(settings)

            self.assertEqual(len(paths), 5)
            for path in paths:
                self.assertTrue(path.exists())
                self.assertTrue(path.is_dir())


if __name__ == "__main__":
    unittest.main()

