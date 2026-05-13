import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

def run():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment")

    # Fix postgres:// → postgresql:// (Supabase/Railway format)
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    engine = create_engine(
        database_url,
        connect_args={
            "connect_timeout": 30,
            "options": "-c statement_timeout=120000",  # 120s — plenty for DDL on Supabase
        },
    )

    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE signals ADD COLUMN IF NOT EXISTS explanation TEXT"))
        conn.commit()
        print("✓ explanation column ready (added or already existed)")

if __name__ == "__main__":
    run()
