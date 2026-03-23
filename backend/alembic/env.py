"""Alembic environment configuration for SQLAlchemy.

This module configures Alembic to work with SQLAlchemy 2.0.
Uses synchronous psycopg2 for migrations to support multi-statement SQL.
"""

from logging.config import fileConfig

from sqlalchemy import String, create_engine, pool, text
from sqlalchemy.engine import Connection

from alembic import context

# Import settings for database URL
from pilot_space.config import get_settings

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models here for autogenerate support
from pilot_space.infrastructure.database.models import Base  # noqa: E402

target_metadata = Base.metadata


def get_database_url() -> str:
    """Get database URL from settings.

    Converts asyncpg URL to psycopg2 for synchronous migrations.
    """
    settings = get_settings()
    url = settings.database_url.get_secret_value()
    # Convert postgresql+asyncpg:// to postgresql://
    return url.replace("postgresql+asyncpg://", "postgresql://")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        version_table="alembic_version",
        version_num_col_type=String(128),
    )

    with context.begin_transaction():
        context.run_migrations()


def _ensure_version_table_width(connection: Connection) -> None:
    """Ensure alembic_version.version_num is wide enough for descriptive IDs.

    Alembic creates the table with varchar(32) by default. Some revision IDs
    exceed 32 chars. This pre-creates or widens the table to varchar(128).
    """
    # Create table if it doesn't exist (with correct width from the start)
    connection.execute(
        text("""
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num varchar(128) NOT NULL,
                CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
            )
        """)
    )
    # If table already existed with varchar(32), widen it
    result = connection.execute(
        text("""
            SELECT character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'alembic_version'
              AND column_name = 'version_num'
        """)
    )
    row = result.fetchone()
    if row and row[0] and row[0] < 128:
        connection.execute(
            text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE varchar(128)")
        )
    connection.commit()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with a connection."""
    _ensure_version_table_width(connection)

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        version_table="alembic_version",
        version_num_col_type=String(128),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with sync engine.

    Uses synchronous psycopg2 driver which supports multi-statement SQL.
    """
    url = get_database_url()

    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
