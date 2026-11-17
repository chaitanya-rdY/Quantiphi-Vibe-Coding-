"""SQLite-backed cache engine: repo metadata, profile, contributions, user settings.

Entries are considered fresh for `ttl` seconds. Stale entries are still readable so the
service layer can fall back to them when GitHub is rate-limiting or unreachable.
"""
from __future__ import annotations

import json
import time

from .config import settings
from .db import connect, init_db


class Cache:
    def __init__(self, db_path: str | None = None, ttl: int | None = None):
        self.db_path = db_path or settings.db_path
        self.ttl = settings.cache_ttl_seconds if ttl is None else ttl
        init_db(self.db_path)

    # ---- helpers -------------------------------------------------------
    def is_fresh(self, fetched_at: float | None) -> bool:
        return fetched_at is not None and (time.time() - fetched_at) < self.ttl

    @staticmethod
    def _key(username: str) -> str:
        return username.strip().lower()

    # ---- profile -------------------------------------------------------
    def get_profile(self, username: str) -> tuple[dict | None, float | None]:
        with connect(self.db_path) as c:
            row = c.execute(
                "SELECT data, fetched_at FROM profiles WHERE username=?", (self._key(username),)
            ).fetchone()
        return (json.loads(row["data"]), row["fetched_at"]) if row else (None, None)

    def set_profile(self, username: str, data: dict) -> None:
        with connect(self.db_path) as c:
            c.execute(
                "INSERT OR REPLACE INTO profiles(username, data, fetched_at) VALUES (?,?,?)",
                (self._key(username), json.dumps(data), time.time()),
            )

    # ---- repos ---------------------------------------------------------
    def get_repos(self, username: str) -> tuple[list[dict] | None, float | None]:
        with connect(self.db_path) as c:
            rows = c.execute(
                "SELECT data, fetched_at FROM repos WHERE username=?", (self._key(username),)
            ).fetchall()
        if not rows:
            return None, None
        return [json.loads(r["data"]) for r in rows], min(r["fetched_at"] for r in rows)

    def set_repos(self, username: str, repos: list[dict]) -> None:
        now = time.time()
        key = self._key(username)
        with connect(self.db_path) as c:
            c.execute("DELETE FROM repos WHERE username=?", (key,))
            c.executemany(
                "INSERT INTO repos(username, name, data, fetched_at) VALUES (?,?,?,?)",
                [(key, r["name"], json.dumps(r), now) for r in repos],
            )

    # ---- contributions -------------------------------------------------
    def get_contributions(self, username: str) -> tuple[dict | None, float | None]:
        with connect(self.db_path) as c:
            row = c.execute(
                "SELECT data, source, fetched_at FROM contributions WHERE username=?",
                (self._key(username),),
            ).fetchone()
        if not row:
            return None, None
        data = json.loads(row["data"])
        data["source"] = row["source"]
        return data, row["fetched_at"]

    def set_contributions(self, username: str, data: dict, source: str) -> None:
        with connect(self.db_path) as c:
            c.execute(
                "INSERT OR REPLACE INTO contributions(username, data, source, fetched_at) VALUES (?,?,?,?)",
                (self._key(username), json.dumps(data), source, time.time()),
            )

    # ---- user settings (key/value) -------------------------------------
    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with connect(self.db_path) as c:
            row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with connect(self.db_path) as c:
            c.execute("INSERT OR REPLACE INTO settings(key, value) VALUES (?,?)", (key, value))

    def get_all_settings(self) -> dict[str, str]:
        with connect(self.db_path) as c:
            return {r["key"]: r["value"] for r in c.execute("SELECT key, value FROM settings")}

    # ---- maintenance ---------------------------------------------------
    def invalidate(self, username: str) -> None:
        key = self._key(username)
        with connect(self.db_path) as c:
            for table in ("profiles", "repos", "contributions"):
                c.execute(f"DELETE FROM {table} WHERE username=?", (key,))
