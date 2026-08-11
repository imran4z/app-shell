"""Health endpoints - liveness plus a per-dependency status readout.

Kept intentionally simple in the template: the DB is the only hard
dependency. Add external services here as the app grows (the blueprint's
health-heartbeat pattern, §10, writes these into a system_health table on
a lifespan loop - do that once you have >1 dependency).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

router = APIRouter(prefix="/api/health", tags=["health"])


class HealthStatus(BaseModel):
    status: str
    services: dict[str, str]


@router.get("", response_model=HealthStatus)
def health() -> HealthStatus:
    services: dict[str, str] = {}
    try:
        from appshell.storage import connect

        with connect().connect() as conn:
            conn.execute(text("SELECT 1"))
        services["postgres"] = "up"
    except Exception:  # noqa: BLE001 - health probes report, never raise
        services["postgres"] = "down"

    overall = "ok" if all(v == "up" for v in services.values()) else "degraded"
    return HealthStatus(status=overall, services=services)
