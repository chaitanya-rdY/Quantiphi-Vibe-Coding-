"""End-to-end API tests with the GitHub client swapped for a fake."""
import pytest
from fastapi.testclient import TestClient

from backend.app.cache import Cache
from backend.app.main import app
from backend.app.routers import portfolio as portfolio_router
from backend.app.services.portfolio import PortfolioService
from backend.tests.test_portfolio import FakeClient


@pytest.fixture
def client(tmp_path):
    cache = Cache(db_path=str(tmp_path / "api.db"), ttl=60)
    app.dependency_overrides[portfolio_router.get_cache] = lambda: cache
    app.dependency_overrides[portfolio_router.get_service] = lambda: PortfolioService(cache, FakeClient())
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_portfolio_endpoint(client):
    r = client.get("/api/portfolio/octocat")
    assert r.status_code == 200
    body = r.json()
    assert body["profile"]["total_stars"] == 8 and len(body["repos"]) == 3


def test_invalid_username(client):
    assert client.get("/api/portfolio/bad..name").status_code == 422


def test_match_persisted_and_used_by_chat(client):
    r = client.post("/api/portfolio/octocat/match", json={"job_description": "Python and Java engineer"})
    assert r.json()["percent"] == 50.0
    assert client.get("/api/portfolio/octocat/match").json()["match"]["percent"] == 50.0
    chat = client.post("/api/portfolio/octocat/chat", json={"question": "How well do they fit the job?"})
    assert "50.0%" in chat.json()["answer"]


def test_bio_and_top_language_chat(client):
    assert "Python" in client.get("/api/portfolio/octocat/bio").json()["bio"]
    ans = client.post("/api/portfolio/octocat/chat", json={"question": "what languages do they know"})
    assert "Python" in ans.json()["answer"]
