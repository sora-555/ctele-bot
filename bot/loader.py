"""Process-wide service container, created once during startup."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bot.config import Settings, get_settings
from bot.services.broadcast import BroadcastService
from bot.services.ctele_service import CTeleService
from bot.services.deletion import DeletionService
from bot.services.sessions import SessionStore
from bot.utils.time import utcnow


@dataclass(slots=True)
class Services:
    settings: Settings
    ctele: CTeleService
    sessions: SessionStore
    deletions: DeletionService
    broadcasts: BroadcastService
    started_at: datetime
    maintenance_enabled: bool = False


_services: Services | None = None
_bot = None


def init_services(bot, settings: Settings | None = None) -> Services:
    global _services, _bot
    resolved = settings or get_settings()
    _bot = bot
    _services = Services(
        settings=resolved,
        ctele=CTeleService(resolved),
        sessions=SessionStore(ttl_seconds=resolved.session_ttl),
        deletions=DeletionService(bot, resolved),
        broadcasts=BroadcastService(bot, resolved),
        started_at=utcnow(),
        maintenance_enabled=resolved.maintenance,
    )
    return _services


def services() -> Services:
    if _services is None:
        raise RuntimeError("services are not initialised yet")
    return _services


def bot():
    if _bot is None:
        raise RuntimeError("bot is not initialised yet")
    return _bot


def reset_services() -> None:
    global _services, _bot
    _services = None
    _bot = None