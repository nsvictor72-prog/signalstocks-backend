"""
Migration: add implied_volatility + cc_premium_estimate to signals table.
Run once: python migrations/add_iv_columns.py
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
        for col, ddl in [
            ("implied_volatility",   "ALTER TABLE signals ADD COLUMN IF NOT EXISTS implied_volatility FLOAT"),
            ("cc_premium_estimate",  "ALTER TABLE signals ADD COLUMN IF NOT EXISTS cc_premium_estimate FLOAT"),
        ]:
            try:
                conn.execute(text(ddl))
                conn.commit()
                print(f"[OK] Added column '{col}' to signals table.")
            except Exception as e:
                msg = str(e).lower()
                if "already exists" in msg or "duplicate column" in msg:
                    print(f"[SKIP] Column '{col}' already exists.")
                else:
                    raise

if __name__ == "__main__":
    run()
