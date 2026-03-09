from __future__ import annotations

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ---------------------------------------------------------------------------
# Load .env file if present (development convenience)
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv  # type: ignore[import]
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; rely solely on real env vars

# ---------------------------------------------------------------------------
# Register all models so their metadata is populated before autogenerate
# ---------------------------------------------------------------------------
# These imports must happen BEFORE target_metadata is set so that all
# Table objects are registered with Base.metadata.
import app.models.user        # noqa: F401, E402
import app.models.job         # noqa: F401, E402
import app.models.bid         # noqa: F401, E402
import app.models.contract    # noqa: F401, E402
import app.models.payment     # noqa: F401, E402
import app.models.message     # noqa: F401, E402
import app.models.submission  # noqa: F401, E402
import app.models.audit_log  # noqa: F401, E402

from app.database.base import Base  # noqa: E402

# ---------------------------------------------------------------------------
# Alembic Config object — gives access to values in alembic.ini
# ---------------------------------------------------------------------------
config = context.config

# Interpret the config file for Python logging unless already configured
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Override sqlalchemy.url from the DATABASE_URL environment variable
# ---------------------------------------------------------------------------
database_url: str | None = os.environ.get("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# Target metadata for 'autogenerate' support
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline migrations
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine.
    Calls to context.execute() will emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migrations
# ---------------------------------------------------------------------------

def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    Creates an Engine and associates a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
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
