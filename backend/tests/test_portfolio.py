import asyncio
from datetime import date

import pytest

from backend.app.cache import Cache
from backend.app.github_client import GitHubError
from backend.app.services import stats
from backend.app.services.portfolio import PortfolioService


class FakeClient:
    def __init__(self):
        self.calls = 0
        self.fail = False

    async def fetch_user(self, u):
        self.calls += 1
        if self.fail:
            raise GitHubError("rate limited", 429)
        return {"login": u, "name": u, "followers": 12, "avatar_url": None}

    async def fetch_repos(self, u):
        self.calls += 1
        if self.fail:
            raise GitHubError("rate limited", 429)
        return [
            {"name": "a", "language": "Python", "stars": 5, "forks": 1, "is_fork": False, "description": ""},
            {"name": "b", "language": "Python", "stars": 2, "forks": 0, "is_fork": False, "description": ""},
            {"name": "c", "language": "Go", "stars": 1, "forks": 0, "is_fork": False, "description": ""},
            {"name": "d", "language": "Rust", "stars": 99, "forks": 9, "is_fork": True, "description": ""},
        ]

    async def fetch_contributions(self, u):
        return None

    async def fetch_events_contributions(self, u):
        return {"total": 3, "days": [{"date": "2026-11-16", "count": 2}, {"date": "2026-11-17", "count": 1}]}


@pytest.fixture
def cache(tmp_path):
    return Cache(db_path=str(tmp_path / "t.db"), ttl=60)


def test_cache_hit_avoids_github(cache):
    client = FakeClient()
    svc = PortfolioService(cache, client)
    asyncio.run(svc.build_portfolio("x"))
    first = client.calls
    out = asyncio.run(svc.build_portfolio("x"))
    assert client.calls == first
    assert out["meta"]["served_from_cache"] is True


def test_stale_fallback_on_rate_limit(tmp_path):
    cache = Cache(db_path=str(tmp_path / "t.db"), ttl=0)  # always stale
    client = FakeClient()
    svc = PortfolioService(cache, client)
    asyncio.run(svc.build_portfolio("x"))
    client.fail = True
    out = asyncio.run(svc.build_portfolio("x"))
    assert out["meta"]["stale"] is True
    assert out["profile"]["followers"] == 12


def test_forks_excluded_from_totals_and_languages(cache):
    out = asyncio.run(PortfolioService(cache, FakeClient()).build_portfolio("x"))
    assert out["profile"]["total_stars"] == 8
    langs = {l["language"]: l["percent"] for l in out["languages"]}
    assert "Rust" not in langs and langs["Python"] == 66.7


def test_streaks():
    days = [{"date": f"2026-11-{d:02d}", "count": 1} for d in (10, 11, 12, 14, 15, 16, 17)]
    s = stats.contribution_stats(days, today=date(2026, 11, 17))
    assert s["current_streak"] == 4 and s["longest_streak"] == 4


def test_settings_roundtrip(cache):
    cache.set_setting("theme", "dark")
    assert cache.get_setting("theme") == "dark"
