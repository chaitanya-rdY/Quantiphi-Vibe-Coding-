# GitHub Developer Portfolio

A developer dashboard that visualizes GitHub activity, repository stats and coding
streaks. FastAPI backend (all business logic) + SQLite cache + static frontend.

## Run

```bash
pip install -r requirements.txt
cp .env.example .env      # add GITHUB_TOKEN for higher limits + contribution heatmap
uvicorn backend.app.main:app --reload
# open http://localhost:8000
```

## Architecture

```
backend/app/
  config.py            settings (env)
  github_client.py     GitHub REST + GraphQL client
  db.py                SQLite connection + schema
  cache.py             TTL cache engine (repos, profile, contributions, settings)
  services/            business logic (portfolio aggregation, match score, ...)
  routers/             HTTP layer
frontend/static/       presentation only (HTML/CSS/JS)
```
