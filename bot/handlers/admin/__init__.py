"""Admin routers, combined into one sub-router."""

from __future__ import annotations

from aiogram import Router

from bot.handlers.admin import (
    broadcast,
    export,
    logs,
    moderation,
    panel,
    roles,
    users,
)

router = Router(name="admin")
router.include_router(panel.router)
router.include_router(users.router)
router.include_router(moderation.router)
router.include_router(broadcast.router)
router.include_router(logs.router)
router.include_router(export.router)
router.include_router(roles.router)

__all__ = ["router"]
