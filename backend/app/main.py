from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .routers import portfolio

app = FastAPI(title="GitHub Developer Portfolio")
app.include_router(portfolio.router)

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"


@app.get("/api/health")
def health():
    return {"status": "ok"}


if FRONTEND.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND / "static"), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(FRONTEND / "index.html")
