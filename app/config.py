from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str
    environment: str
    database_path: Path
    storage_root: Path
    secret_key: str
    max_upload_bytes: int
    evaluation_mode: str = "worker"

    @property
    def submissions_dir(self) -> Path:
        return self.storage_root / "submissions"

    @property
    def ground_truth_dir(self) -> Path:
        return self.storage_root / "ground-truth"

    @property
    def bundles_dir(self) -> Path:
        return self.storage_root / "bundles"

    @property
    def exports_dir(self) -> Path:
        return self.storage_root / "exports"


def load_settings() -> Settings:
    project_root = Path(__file__).resolve().parent.parent
    data_root = project_root / "var"

    return Settings(
        app_name=os.getenv("APP_NAME", "NTCIR-19 ModelRetrieval Submissions"),
        environment=os.getenv("APP_ENV", "development"),
        database_path=Path(os.getenv("DATABASE_PATH", data_root / "app.sqlite3")),
        storage_root=Path(os.getenv("STORAGE_ROOT", data_root / "storage")),
        secret_key=os.getenv("SECRET_KEY", "change-me-before-production"),
        max_upload_bytes=int(os.getenv("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024))),
        evaluation_mode=os.getenv("EVALUATION_MODE", "worker"),
    )


settings = load_settings()

