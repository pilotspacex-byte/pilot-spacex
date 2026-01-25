"""Database infrastructure for Pilot Space.

Components:
- engine: SQLAlchemy async engine configuration
- base: Base model with UUID PK, timestamps, soft delete
- models/: SQLAlchemy ORM models
- repositories/: Data access layer (Repository pattern)

Database: PostgreSQL 16+ via Supabase with pgvector extension
"""

from pilot_space.infrastructure.database.engine import (
    dispose_engine,
    get_db_session,
    get_engine,
    get_session_factory,
    test_connection,
)

__all__ = [
    "dispose_engine",
    "get_db_session",
    "get_engine",
    "get_session_factory",
    "test_connection",
]
