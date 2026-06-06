
from __future__ import annotations
"""
Alembic environment — v29.0

Supports both sync and async migrations.
Uses DATABASE_URL from environment.
"""

import os
import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context

# Import all models so Alembic sees them
from database.models import Base

config = context.config
fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")

# v29: Use DATABASE_URL from environment
database_url = os.environ.get(
    "DATABASE_URL",
    "sqlite+aiosqlite:///data/arki.db"
)

# Convert async URL to sync for Alembic migrations
sync_url = database_url.replace("+aiosqlite", "").replace("+asyncpg", "+psycopg2")
if "postgresql" in sync_url and "+psycopg2" not in sync_url:
    sync_url = sync_url.replace("postgresql://", "postgresql+psycopg2://")

config.set_main_option("sqlalchemy.url", sync_url)

target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


