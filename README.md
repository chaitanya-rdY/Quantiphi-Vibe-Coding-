# DevFolio — GitHub Developer Portfolio

A professional developer dashboard that visualizes GitHub activity, repository stats and
coding streaks. FastAPI backend (all business logic) + SQLite cache + dependency-free
vanilla-JS frontend (presentation only).

## Run

```bash
pip install -r requirements.txt
cp .env.example .env        # set GITHUB_TOKEN (recommended)
uvicorn backend.app.main:app --reload
# open http://localhost:8000   (or http://localhost:8000/#<username>)
python -m pytest -q         # tests
```

`GITHUB_TOKEN` (no scopes needed) raises the REST limit from 60 to 5000 req/hr and enables the
GraphQL contribution calendar. Without it the heatmap falls back to recent public events
(approximate) and the UI says so.

## Features

| Requirement | Where |
|---|---|
| Contribution heatmap (intensity-coloured) | `services/stats.py` (levels 0-4, streaks) → `render.js` |
| Repository cards (stars, forks, language, description) | `GitHubClient.fetch_repos` → `render.js` |
| Profile header (followers, total stars, top-languages pie) | `services/portfolio.py`, `stats.language_breakdown` |
| GitHub REST + GraphQL integration | `github_client.py` |
| SQLite caching engine | `cache.py`, `db.py` |
| **Tech Stack Compatibility** match % badge | `services/match.py`, `routers/match.py` |
| **Extra 1:** Ask-the-Portfolio chat assistant | `services/assistant.py::answer` |
| **Extra 2:** AI-style Bio & Pitch generator | `services/assistant.py::generate_bio` |

## Architecture

```
backend/app/
  config.py            env-driven settings
  github_client.py     async REST + GraphQL client, error mapping (404 / 429 / 502)
  db.py                SQLite connection + schema
  cache.py             TTL cache: profiles, repos, contributions, key/value user settings
  services/
    stats.py           pure math: language %, streaks, heatmap levels, totals
    portfolio.py       cache-first orchestration, stale-on-error fallback
    match.py           job-description keyword extraction + weighted match score
    assistant.py       grounded chat answers + bio/pitch generation
  routers/             thin HTTP layer + validation
frontend/              HTML/CSS/ES modules; renders server-computed data only
```

### API

- `GET  /api/portfolio/{user}?refresh=false` — profile, languages, repos, contributions, meta
- `DELETE /api/cache/{user}` — invalidate cache
- `POST /api/portfolio/{user}/match` `{job_description}` — match %, matched/missing/bonus languages
- `GET  /api/portfolio/{user}/match` — last saved match + JD (stored in SQLite settings)
- `POST /api/portfolio/{user}/chat` `{question}` — grounded answer + suggested questions
- `GET  /api/portfolio/{user}/bio` — headline, bio, highlights, tailored pitch

### Design decisions

- **Cache-first with stale fallback:** fresh (TTL 15 min) → served from SQLite; expired → refetch;
  GitHub down/rate-limited → serve stale data and flag `meta.stale`.
- **Match score:** languages are extracted from the JD directly (`Python`) or via implied
  frameworks (`Django → Python`, `React → JavaScript`), weighted by mention count; score =
  weighted share the user has in non-fork repos. Ambiguous words (`Go`, `R`, `C`) are matched
  case-sensitively so "go to market" doesn't count. Fully explainable and deterministic.
- **Chat extras are grounded:** every answer is built from cached data, so nothing is hallucinated.
  The module boundary makes it easy to swap in an LLM later.
- **Security:** username validated by regex; frontend builds DOM with `textContent` (no `innerHTML`),
  so repo descriptions can't inject markup; the token never leaves the server.
