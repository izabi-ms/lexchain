"""Database configuration for LexChain.

A local SQLite database is used by default for a frictionless development setup.
Set DATABASE_URL to a PostgreSQL URL for a shared development or hosted environment.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env", override=False)

_default_db_path = BACKEND_DIR / "lexchain.db"
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{_default_db_path.as_posix()}",
).strip()

if not SQLALCHEMY_DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{_default_db_path.as_posix()}"

_engine_kwargs: dict = {"pool_pre_ping": True}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite:"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(SQLALCHEMY_DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
