import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from dotenv import load_dotenv

# --- Load .env ---
load_dotenv()
db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise RuntimeError("DATABASE_URL is not set. Check your .env")

# This is the Alembic Config object
config = context.config

# Set sqlalchemy.url from .env (override alembic.ini)
config.set_main_option("sqlalchemy.url", db_url)

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Import Base & models so Alembic thấy metadata ---
from configs import db
from db.models import *  # đảm bảo đã import tất cả model

target_metadata = db.metadata

# Tùy chọn so sánh để autogenerate chính xác hơn
COMPARE_KW = dict(
    compare_type=True,
    compare_server_default=True,
)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **COMPARE_KW
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,  # SQLAlchemy 2.0
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, **COMPARE_KW
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
