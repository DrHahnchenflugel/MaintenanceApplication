import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine, Connection


def _build_db_url() -> URL:
    return URL.create(
        drivername="postgresql+psycopg2",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ["POSTGRES_DB"],
    )


_engine: Engine = create_engine(
    _build_db_url(),
    pool_pre_ping=True,
    future=True,
)


def get_engine() -> Engine:
    """Return the shared SQLAlchemy engine (connection pool)."""
    return _engine


@contextmanager
def get_connection() -> Connection:
    """
    Context manager that yields a DB connection and
    ensures it is properly closed / returned to the pool.
    """
    conn = _engine.begin()
    try:
        yield conn
    finally:
        pass
