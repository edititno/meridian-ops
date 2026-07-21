"""Database connection helper.

Uses DATABASE_URL (PostgreSQL on Railway or any cloud Postgres).
Falls back to a local SQLite file for development so the app always runs.
"""
import os
from sqlalchemy import create_engine

DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Railway/Heroku style URLs sometimes use postgres:// which SQLAlchemy rejects
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

IS_SQLITE = not DATABASE_URL
if IS_SQLITE:
    DATABASE_URL = "sqlite:///ops_local.db"

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    return _engine
