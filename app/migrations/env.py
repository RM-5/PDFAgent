import os
import sys
from pathlib import Path
from logging.config import fileConfig
 
from dotenv import load_dotenv
from sqlalchemy import engine_from_config
from sqlalchemy import pool
 
from alembic import context
 
# ── Make sure the app package is importable ──────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
 
# ── Load .env so DATABASE_URL is available ───────────────────────────────────
# Explicit path — .env lives at PDFAgent/.env, this file is at PDFAgent/app/migrations/env.py
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
 
# ── Import your models so autogenerate can see them ──────────────────────────
from app.db.database import Base
from app.db import models  # noqa: F401 — imported so Base.metadata picks up all tables
 
# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
 
# ── Override the URL from alembic.ini with the one from .env ─────────────────
# Alembic runs synchronously, so strip the +asyncpg driver suffix
db_url = os.getenv("DATABASE_URL", "")
if not db_url:
    raise RuntimeError(
        f"DATABASE_URL not found. Checked: {env_path}. "
        f"Make sure your .env file exists there and contains DATABASE_URL=..."
    )
db_url = db_url.replace("+asyncpg", "")
config.set_main_option("sqlalchemy.url", db_url)
 
# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
 
# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata
 
# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.
 
 
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
 
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.
 
    Calls to context.execute() here emit the given string to the
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
 
 
def run_migrations_online() -> None:
    """Run migrations in 'online' mode.
 
    In this scenario we need to create an Engine
    and associate a connection with the context.
 
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
 
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
 
        with context.begin_transaction():
            context.run_migrations()
 
 
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
 