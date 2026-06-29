from __future__ import annotations

from pathlib import Path

from app.config import Settings


def ensure_storage(settings: Settings) -> list[Path]:
    paths = [
        settings.storage_root,
        settings.submissions_dir,
        settings.ground_truth_dir,
        settings.bundles_dir,
        settings.exports_dir,
    ]

    for path in paths:
        path.mkdir(parents=True, exist_ok=True)

    return paths

