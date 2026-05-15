"""
Migration: add is_paper_trade + user_id columns to portfolio table.
Run once: python migrations/add_paper_trade_columns.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import text
from database import get_engine

def run():
    engine = get_engine()
    with engine.connect() as conn:
        for sql, label in [
            ("ALTER TABLE portfolio ADD COLUMN IF NOT EXISTS is_paper_trade BOOLEAN DEFAULT FALSE",
             "is_paper_trade"),
            ("ALTER TABLE portfolio ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES app_users(id)",
             "user_id"),
        ]:
            try:
                conn.execute(text(sql))
                conn.commit()
                print(f"[OK] Added column '{label}' to portfolio table.")
            except Exception as e:
                msg = str(e).lower()
                if "already exists" in msg or "duplicate column" in msg:
                    print(f"[SKIP] Column '{label}' already exists.")
                else:
                    raise

if __name__ == "__main__":
    run()
