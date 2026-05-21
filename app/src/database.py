from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import get_settings


settings = get_settings()

engine_kwargs = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    engine_kwargs.update({"connect_args": {"check_same_thread": False}, "poolclass": StaticPool})

engine: Engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def detect_booking_table() -> str:
    try:
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
    except OperationalError as exc:
        raise RuntimeError(
            f"Could not open booking database from DATABASE_URL={settings.database_url!r}. "
            "Check that visa/noshow.db exists, or set DATABASE_URL to an absolute SQLite path."
        ) from exc

    for table_name in table_names:
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if {"booking_id", "no_show"}.issubset(columns):
            return table_name
    if not table_names:
        raise RuntimeError(
            f"No tables found in booking database from DATABASE_URL={settings.database_url!r}."
        )
    raise RuntimeError(
        "No booking table found. Expected a table with at least 'booking_id' and 'no_show' columns. "
        f"Available tables: {', '.join(table_names)}"
    )


BOOKING_TABLE = detect_booking_table()


def table_exists(table_name: str) -> bool:
    return table_name in inspect(engine).get_table_names()


def table_columns(table_name: str | None = None) -> list[str]:
    return [column["name"] for column in inspect(engine).get_columns(table_name or BOOKING_TABLE)]


def assert_known_column(column: str, table_name: str | None = None) -> str:
    if column not in table_columns(table_name):
        raise ValueError(f"Unknown column: {column}")
    return column


def fetch_all_dicts(sql: str, params: dict | None = None) -> list[dict]:
    with session_scope() as db:
        result = db.execute(text(sql), params or {})
        return [dict(row._mapping) for row in result]


def fetch_one_dict(sql: str, params: dict | None = None) -> dict:
    with session_scope() as db:
        result = db.execute(text(sql), params or {}).mappings().first()
        return dict(result) if result else {}
