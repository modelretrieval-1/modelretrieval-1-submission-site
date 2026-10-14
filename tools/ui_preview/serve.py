"""Run the demo server without starting or recovering the evaluation worker."""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.ui_preview.common import DEFAULT_ROOT, REPO_ROOT, preview_settings  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    if not (root / "manifest.json").is_file() or not (root / "app.sqlite3").is_file():
        parser.error(f"No seeded environment at {root}; run seed_demo.py first.")
    manifest = json.loads((root / "manifest.json").read_text())
    if Path(manifest["root"]) != root:
        parser.error("Seed root has moved; preserved storage paths are absolute. Seed a new root.")
    settings = preview_settings(root)
    os.environ.update(
        {
            "DATABASE_PATH": str(settings.database_path),
            "STORAGE_ROOT": str(settings.storage_root),
            "SECRET_KEY": settings.secret_key,
            "APP_ENV": "development",
            "EVALUATION_MODE": "eager",
        }
    )
    os.chdir(REPO_ROOT)
    import uvicorn

    from app.main import create_app

    # Pass settings explicitly: importing common also imports app.config before
    # these environment variables are set, so its module singleton is stale.
    config = uvicorn.Config(create_app(settings), host="127.0.0.1", port=args.port)
    # Bind before lifespan initialization so a bind error stays visible even if
    # Alembic's migration logging config disables the uvicorn.error logger.
    with config.bind_socket() as server_socket:
        uvicorn.Server(config).run(sockets=[server_socket])


if __name__ == "__main__":
    main()
