from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..cache import Cache
from ..github_client import GitHubError
from ..services import match as match_service
from ..services.portfolio import PortfolioService
from .portfolio import get_cache, get_service, validate_username

router = APIRouter(prefix="/api", tags=["match"])


class MatchRequest(BaseModel):
    job_description: str = Field(..., min_length=3, max_length=20000)


@router.post("/portfolio/{username}/match")
async def compute_match(
    username: str,
    body: MatchRequest,
    service: PortfolioService = Depends(get_service),
    cache: Cache = Depends(get_cache),
):
    validate_username(username)
    try:
        repos, _, _ = await service.get_repos(username)  # cache-first
    except GitHubError as e:
        raise HTTPException(e.status_code, e.message)
    result = match_service.compute_match(body.job_description, repos)
    cache.set_setting(f"jd:{username.lower()}", body.job_description)
    cache.set_setting(f"match:{username.lower()}", json.dumps(result))
    return result


@router.get("/portfolio/{username}/match")
def last_match(username: str, cache: Cache = Depends(get_cache)):
    validate_username(username)
    raw = cache.get_setting(f"match:{username.lower()}")
    return {
        "match": json.loads(raw) if raw else None,
        "job_description": cache.get_setting(f"jd:{username.lower()}"),
    }
