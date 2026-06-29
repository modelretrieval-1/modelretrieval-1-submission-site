from __future__ import annotations

import argparse
import sqlite3

from app.accounts import create_organizer
from app.config import settings
from app.db import connect, initialize_database
from app.storage import ensure_storage


def create_admin(username: str, display_name: str) -> int:
    ensure_storage(settings)
    initialize_database(settings.database_path)

    try:
        with connect(settings.database_path) as connection:
            account = create_organizer(
                connection,
                username=username,
                display_name=display_name,
            )
    except sqlite3.IntegrityError:
        print(f"Organizer '{username}' already exists.")
        return 1

    print("Organizer created.")
    print(f"Username: {account.user_id}")
    print(f"Password: {account.password}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="ModelRetrieval submission system utilities.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_admin_parser = subparsers.add_parser("create-admin", help="Create an organizer user.")
    create_admin_parser.add_argument("--username", required=True)
    create_admin_parser.add_argument("--display-name", required=True)

    args = parser.parse_args()

    if args.command == "create-admin":
        return create_admin(username=args.username, display_name=args.display_name)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

