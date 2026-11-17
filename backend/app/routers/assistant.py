from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..cache import Cache
from ..github_client import GitHubError
from ..services import assistant
from ..services.portfolio import PortfolioService
from .portfolio import get_cache, get_service, validate_username

router = APIRouter(prefix="/api", tags=["assistant"])


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=500)


async def _load(username: str, service: PortfolioService, cache: Cache):
    validate_username(username)
    try:
        portfolio = await service.build_portfolio(username)
    except GitHubError as e:
        raise HTTPException(e.status_code, e.message)
    raw = cache.get_setting(f"match:{username.lower()}")
    return portfolio, (json.loads(raw) if raw else None)


@router.post("/portfolio/{username}/chat")
async def chat(
    username: str,
    body: ChatRequest,
    service: PortfolioService = Depends(get_service),
    cache: Cache = Depends(get_cache),
):
    portfolio, match = await _load(username, service, cache)
    return assistant.answer(body.question, portfolio, match)


@router.get("/portfolio/{username}/bio")
async def bio(
    username: str,
    service: PortfolioService = Depends(get_service),
    cache: Cache = Depends(get_cache),
):
    portfolio, match = await _load(username, service, cache)
    return assistant.generate_bio(portfolio, match)
