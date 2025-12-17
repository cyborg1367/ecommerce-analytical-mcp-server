from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def normalize_sqlalchemy_dsn(dsn: str) -> str:
    dsn = (dsn or "").strip()
    if dsn.startswith("postgresql://"):
        return dsn.replace("postgresql://", "postgresql+psycopg://", 1)
    if dsn.startswith("postgres://"):
        return dsn.replace("postgres://", "postgresql+psycopg://", 1)
    return dsn


def build_engine(dsn: str) -> Engine:
    return create_engine(
        dsn,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        future=True,
    )
