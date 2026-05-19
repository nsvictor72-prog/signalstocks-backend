"""Migration: add email verification and password reset columns to app_users"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_engine
from sqlalchemy import text


def run():
    engine = get_engine()
    with engine.connect() as conn:
        cols = [
            "ALTER TABLE app_users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE app_users ADD COLUMN IF NOT EXISTS verification_token VARCHAR(255)",
            "ALTER TABLE app_users ADD COLUMN IF NOT EXISTS verification_token_expires TIMESTAMP",
            "ALTER TABLE app_users ADD COLUMN IF NOT EXISTS reset_token VARCHAR(255)",
            "ALTER TABLE app_users ADD COLUMN IF NOT EXISTS reset_token_expires TIMESTAMP",
        ]
        for stmt in cols:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass  # column already exists (SQLite doesn't support IF NOT EXISTS)

        # Mark all existing users as verified — they registered before this requirement
        conn.execute(text(
            "UPDATE app_users SET is_verified = TRUE "
            "WHERE is_verified = FALSE AND verification_token IS NULL"
        ))
        conn.commit()

    print("[OK] email verification columns added (existing users marked verified)")


if __name__ == "__main__":
    run()
