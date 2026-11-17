"""Thin async client for the GitHub REST and GraphQL APIs."""
from __future__ import annotations

import httpx

from .config import settings


class GitHubError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


CONTRIBUTIONS_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionCount }
        }
      }
    }
  }
}
"""


class GitHubClient:
    def __init__(self, token: str | None = None):
        self.token = token if token is not None else settings.github_token

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "github-dev-portfolio",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _get(self, client: httpx.AsyncClient, path: str, params: dict | None = None):
        resp = await client.get(f"{settings.github_rest_url}{path}", params=params)
        if resp.status_code == 404:
            raise GitHubError("GitHub user not found", 404)
        if resp.status_code in (403, 429):
            raise GitHubError("GitHub API rate limit exceeded. Add a GITHUB_TOKEN or retry later.", 429)
        if resp.status_code >= 400:
            raise GitHubError(f"GitHub API error ({resp.status_code})", 502)
        return resp.json()

    async def fetch_user(self, username: str) -> dict:
        async with httpx.AsyncClient(headers=self._headers(), timeout=settings.http_timeout) as c:
            data = await self._get(c, f"/users/{username}")
        return {
            "login": data["login"],
            "name": data.get("name") or data["login"],
            "avatar_url": data.get("avatar_url"),
            "bio": data.get("bio"),
            "location": data.get("location"),
            "company": data.get("company"),
            "blog": data.get("blog"),
            "html_url": data.get("html_url"),
            "followers": data.get("followers", 0),
            "following": data.get("following", 0),
            "public_repos": data.get("public_repos", 0),
            "created_at": data.get("created_at"),
        }

    async def fetch_repos(self, username: str, max_repos: int = 100) -> list[dict]:
        """Public, non-fork repos (paginated), normalised to the fields we need."""
        repos: list[dict] = []
        async with httpx.AsyncClient(headers=self._headers(), timeout=settings.http_timeout) as c:
            page = 1
            while len(repos) < max_repos:
                batch = await self._get(
                    c,
                    f"/users/{username}/repos",
                    {"per_page": 100, "page": page, "type": "owner", "sort": "pushed"},
                )
                if not batch:
                    break
                repos.extend(batch)
                if len(batch) < 100:
                    break
                page += 1
        return [
            {
                "name": r["name"],
                "full_name": r["full_name"],
                "description": r.get("description") or "",
                "html_url": r["html_url"],
                "language": r.get("language"),
                "stars": r.get("stargazers_count", 0),
                "forks": r.get("forks_count", 0),
                "topics": r.get("topics", []),
                "is_fork": bool(r.get("fork")),
                "pushed_at": r.get("pushed_at"),
            }
            for r in repos[:max_repos]
        ]

    async def fetch_contributions(self, username: str) -> dict | None:
        """Daily contribution counts via GraphQL. Requires a token; returns None without one."""
        if not self.token:
            return None
        async with httpx.AsyncClient(headers=self._headers(), timeout=settings.http_timeout) as c:
            resp = await c.post(
                settings.github_graphql_url,
                json={"query": CONTRIBUTIONS_QUERY, "variables": {"login": username}},
            )
        if resp.status_code >= 400:
            return None
        payload = resp.json()
        user = (payload.get("data") or {}).get("user")
        if not user:
            return None
        cal = user["contributionsCollection"]["contributionCalendar"]
        days = [
            {"date": d["date"], "count": d["contributionCount"]}
            for w in cal["weeks"]
            for d in w["contributionDays"]
        ]
        return {"total": cal["totalContributions"], "days": days}

    async def fetch_events_contributions(self, username: str) -> dict:
        """Token-less fallback: approximate daily activity from public events (last ~90 days)."""
        counts: dict[str, int] = {}
        async with httpx.AsyncClient(headers=self._headers(), timeout=settings.http_timeout) as c:
            for page in (1, 2, 3):
                try:
                    events = await self._get(
                        c, f"/users/{username}/events/public", {"per_page": 100, "page": page}
                    )
                except GitHubError:
                    break
                if not events:
                    break
                for e in events:
                    day = e["created_at"][:10]
                    n = len(e.get("payload", {}).get("commits", [])) if e["type"] == "PushEvent" else 1
                    counts[day] = counts.get(day, 0) + max(n, 1)
        days = [{"date": d, "count": n} for d, n in sorted(counts.items())]
        return {"total": sum(counts.values()), "days": days}
