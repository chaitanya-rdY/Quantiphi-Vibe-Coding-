"""Cache-aware orchestration: serve from SQLite when fresh, hit GitHub otherwise,
and fall back to stale cache if GitHub is rate-limited or unreachable."""
from __future__ import annotations

import httpx

from ..cache import Cache
from ..github_client import GitHubClient, GitHubError
from . import stats


class PortfolioService:
    def __init__(self, cache: Cache, client: GitHubClient):
        self.cache = cache
        self.client = client

    async def _cached(self, getter, setter, fetcher, refresh: bool):
        """Returns (value, from_cache, stale)."""
        value, fetched_at = getter()
        if value is not None and not refresh and self.cache.is_fresh(fetched_at):
            return value, True, False
        try:
            fresh = await fetcher()
        except (GitHubError, httpx.HTTPError):
            if value is not None:  # serve stale rather than fail
                return value, True, True
            raise
        setter(fresh)
        return fresh, False, False

    async def get_profile(self, username: str, refresh: bool = False):
        return await self._cached(
            lambda: self.cache.get_profile(username),
            lambda d: self.cache.set_profile(username, d),
            lambda: self.client.fetch_user(username),
            refresh,
        )

    async def get_repos(self, username: str, refresh: bool = False):
        return await self._cached(
            lambda: self.cache.get_repos(username),
            lambda d: self.cache.set_repos(username, d),
            lambda: self.client.fetch_repos(username),
            refresh,
        )

    async def get_contributions(self, username: str, refresh: bool = False) -> tuple[dict, bool, bool]:
        cached, fetched_at = self.cache.get_contributions(username)
        if cached is not None and not refresh and self.cache.is_fresh(fetched_at):
            return cached, True, False
        try:
            data = await self.client.fetch_contributions(username)
            source = "graphql"
            if data is None:
                data = await self.client.fetch_events_contributions(username)
                source = "events"
        except (GitHubError, httpx.HTTPError):
            if cached is not None:
                return cached, True, True
            return {"total": 0, "days": [], "source": "unavailable"}, False, False
        self.cache.set_contributions(username, data, source)
        return {**data, "source": source}, False, False

    async def build_portfolio(self, username: str, refresh: bool = False) -> dict:
        profile, p_cached, p_stale = await self.get_profile(username, refresh)
        repos, r_cached, r_stale = await self.get_repos(username, refresh)
        contrib, c_cached, c_stale = await self.get_contributions(username, refresh)

        own = [r for r in repos if not r["is_fork"]]
        own.sort(key=lambda r: (r["stars"], r["forks"]), reverse=True)
        totals = stats.repo_totals(repos)

        return {
            "profile": {**profile, **totals},
            "languages": stats.language_breakdown(repos),
            "repos": own,
            "contributions": {
                **stats.contribution_stats(contrib.get("days", [])),
                "source": contrib.get("source", "unavailable"),
            },
            "meta": {
                "served_from_cache": p_cached and r_cached,
                "stale": p_stale or r_stale or c_stale,
                "cache_ttl_seconds": self.cache.ttl,
            },
        }
