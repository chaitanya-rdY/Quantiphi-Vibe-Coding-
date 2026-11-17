from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Query

from ..cache import Cache
from ..github_client import GitHubClient, GitHubError
from ..services.portfolio import PortfolioService

router = APIRouter(prefix="/api", tags=["portfolio"])

USERNAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")

_cache: Cache | None = None


def get_cache() -> Cache:
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache


def get_service(cache: Cache = Depends(get_cache)) -> PortfolioService:
    return PortfolioService(cache, GitHubClient())


def validate_username(username: str) -> str:
    if not USERNAME_RE.match(username):
        raise HTTPException(422, "Invalid GitHub username")
    return username


@router.get("/portfolio/{username}")
async def get_portfolio(
    username: str,
    refresh: bool = Query(False, description="Bypass the cache and re-fetch from GitHub"),
    service: PortfolioService = Depends(get_service),
):
    validate_username(username)
    try:
        return await service.build_portfolio(username, refresh=refresh)
    except GitHubError as e:
        raise HTTPException(e.status_code, e.message)


@router.delete("/cache/{username}")
def clear_cache(username: str, cache: Cache = Depends(get_cache)):
    validate_username(username)
    cache.invalidate(username)
    return {"status": "cleared", "username": username}
