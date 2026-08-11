"""FastAPI assembly - order is firm (BLUEPRINT.md §5):

  1. lifespan: load_dotenv(override=True) -> configure structlog ->
     apply migrations (best-effort).
  2. FastAPI().
  3. CORSMiddleware, explicit localhost dev origins only.
  4. Routers.
  5. mount_ui() LAST: /assets static, then a catch-all that 404s JSON for
     api/*, serves real files with containment check, falls back to
     index.html for SPA routing. No-op when dist is missing (dev lane).

The .env is canonical for SECRETS - hence override=True. Infrastructure
wiring must therefore use env names the .env never defines (compose sets
APPSHELL_POSTGRES_HOST; see storage/db.py).
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

import structlog
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from appshell.observability import configure_logging

_logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    load_dotenv(override=True)  # .env is canonical for secrets
    configure_logging(os.environ.get("APPSHELL_LOG_LEVEL", "INFO"))
    # Auto-migrate on boot: makes the docker run-lane zero-step. Best-effort
    # so the API (and its /api/health) still boots when Postgres is down.
    try:
        from appshell.storage import apply_migrations

        applied = apply_migrations()
        if applied:
            _logger.info("boot.migrations_applied", files=applied)
    except Exception as exc:  # noqa: BLE001
        _logger.warning("boot.migrations_failed", error=str(exc)[:300])
    yield


app = FastAPI(title="App Shell", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type"],
)

from appshell.api.routes.assistant import router as assistant_router  # noqa: E402
from appshell.api.routes.health import router as health_router  # noqa: E402
from appshell.api.routes.items import router as items_router  # noqa: E402
from appshell.api.routes.profiles import router as profiles_router  # noqa: E402
from appshell.api.routes.users import router as users_router  # noqa: E402

app.include_router(health_router)
app.include_router(items_router)
app.include_router(profiles_router)
app.include_router(users_router)
app.include_router(assistant_router)


def mount_ui(app: FastAPI) -> None:
    """Serve the built SPA. Must be called LAST so API routes win."""
    dist = Path(os.environ.get("APPSHELL_UI_DIST", "ui/dist")).resolve()
    if not (dist / "index.html").exists():
        _logger.info("boot.ui_dist_missing", path=str(dist))
        return

    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> Response:
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "not found"}, status_code=404)
        candidate = (dist / full_path).resolve()
        if candidate.is_file() and candidate.is_relative_to(dist):
            return FileResponse(candidate)
        return FileResponse(dist / "index.html")


mount_ui(app)
