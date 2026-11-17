"""SQLite connection helper and schema."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    username   TEXT PRIMARY KEY,
    data       TEXT NOT NULL,
    fetched_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS repos (
    username   TEXT NOT NULL,
    name       TEXT NOT NULL,
    data       TEXT NOT NULL,
    fetched_at REAL NOT NULL,
    PRIMARY KEY (username, name)
);
CREATE TABLE IF NOT EXISTS contributions (
    username   TEXT PRIMARY KEY,
    data       TEXT NOT NULL,
    source     TEXT NOT NULL,
    fetched_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def get_db_path() -> str:
    return settings.db_path


@contextmanager
def connect(path: str | None = None):
    conn = sqlite3.connect(path or get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(path: str | None = None) -> None:
    with connect(path) as conn:
        conn.executescript(SCHEMA)
