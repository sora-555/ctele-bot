"""Operational endpoints for the host's uptime probes."""

from __future__ import annotations

import time

from fastapi import APIRouter
from sqlalchemy import text

from bot import __version__
from bot.database.base import database_size_bytes, session_scope
from bot.loader import services
from bot.utils.time import humanize_uptime, utcnow

router = APIRouter()
STARTED_AT = utcnow()
STARTED_MONOTONIC = time.monotonic()


@router.get("/", include_in_schema=False)
async def root() -> dict:
    return {
        "service": "cosplaytele-bot",
        "version": __version__,
        "uptime_seconds": int(time.monotonic() - STARTED_MONOTONIC),
        "uptime": humanize_uptime(STARTED_AT),
    }


@router.get("/healthz", include_in_schema=False)
async def healthz() -> dict:
    """Liveness: the process is up and serving."""
    return {"ok": True}


@router.get("/readyz", include_in_schema=False)
async def readyz() -> dict:
    """Readiness: the database answers and the source is reachable."""
    database_ok = True
    try:
        async with session_scope() as session:
            await session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        database_ok = False

    source_error: str | None = None
    try:
        source_error = services().ctele.last_error
    except RuntimeError:
        source_error = "services are not initialised"
    return {
        "ok": database_ok,
        "database": database_ok,
        "database_bytes": database_size_bytes(),
        "source_last_error": source_error,
    }