"""Migration: create the users table for JWT auth"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Base, User, get_engine


def run():
    engine = get_engine()
    Base.metadata.create_all(engine, tables=[User.__table__])
    print("[OK] users table created (or already exists)")


if __name__ == "__main__":
    run()
