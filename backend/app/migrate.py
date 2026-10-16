"""Tiny, safe schema upgrade for databases created before login existed.

`Base.metadata.create_all` creates NEW tables (users, activity_logs) but never alters existing ones.
Your live Neon DB already has `assessments` without `user_id`, so we add that column if it is missing.
"""
from sqlalchemy import inspect, text

from app.core.logging import get_logger
from app.db import engine

logger = get_logger(__name__)


def run() -> None:
    insp = inspect(engine)
    if "assessments" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("assessments")}
        with engine.begin() as conn:
            if "user_id" not in cols:
                logger.info("Migrating: adding assessments.user_id")
                conn.execute(text("ALTER TABLE assessments ADD COLUMN user_id INTEGER"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_assessments_user_id ON assessments (user_id)"))
