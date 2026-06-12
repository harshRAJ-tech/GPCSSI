# File: backend/scripts/seed_admin.py
"""
Seed an initial SYSTEM_ADMIN account.

WHY: Without an open registration endpoint, the system needs a way to
create the first admin. This CLI reads the password from the environment
(SEED_ADMIN_PASSWORD), never from the command line or source, so it does
not leak into shell history or the repo. Run once after the DB is up:

    SEED_ADMIN_PASSWORD='a-strong-password' \\
      python -m scripts.seed_admin --username admin --full-name 'Site Admin'

It is idempotent on username: if the admin already exists, it does
nothing rather than erroring.
"""
import argparse
import os
import sys

from app.core.database import SessionLocal
from app.core.init_db import init_db
from app.models.enums import UserRole
from app.services.user_service import UsernameTaken, create_user


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed a SYSTEM_ADMIN user.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--full-name", required=True)
    args = parser.parse_args()

    password = os.environ.get("SEED_ADMIN_PASSWORD")
    if not password:
        print(
            "ERROR: set SEED_ADMIN_PASSWORD in the environment (min 12 chars).",
            file=sys.stderr,
        )
        return 2
    if len(password) < 12:
        print("ERROR: SEED_ADMIN_PASSWORD must be at least 12 characters.", file=sys.stderr)
        return 2

    # Ensure tables exist before inserting.
    init_db()

    db = SessionLocal()
    try:
        create_user(
            db,
            username=args.username,
            full_name=args.full_name,
            password=password,
            role=UserRole.SYSTEM_ADMIN,
        )
        db.commit()
        print(f"Created SYSTEM_ADMIN '{args.username}'.")
    except UsernameTaken:
        db.rollback()
        print(f"User '{args.username}' already exists; nothing to do.")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
