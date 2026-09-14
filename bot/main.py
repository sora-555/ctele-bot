"""Dispatcher factory: middleware chain, routers, error handling."""

from __future__ import annotations

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import Settings
from bot.handlers import account, browse, errors, fallback, posts, start
from bot.handlers.admin import router as admin_router
from bot.middlewares.admin import AdminMiddleware
from bot.middlewares.db import DbSessionMiddleware
from bot.middlewares.logging import LoggingMiddleware
from bot.middlewares.maintenance import MaintenanceMiddleware
from bot.middlewares.throttle import ThrottleMiddleware
from bot.middlewares.user import UserMiddleware


def build_dispatcher(settings: Settings) -> Dispatcher:
    """Assemble the dispatcher.

    Middleware order is deliberate: logging -> db -> admin -> user ->
    maintenance -> throttle. `admin` runs before `user` so the block and age
    gates can exempt admins, and `user` runs before `maintenance` so role
    resolution is already done when the lock is evaluated.
    """
    dispatcher = Dispatcher(storage=MemoryStorage())

    for observer in (dispatcher.message, dispatcher.callback_query):
        observer.outer_middleware(LoggingMiddleware())
        observer.outer_middleware(DbSessionMiddleware())
        observer.outer_middleware(AdminMiddleware())
        observer.outer_middleware(UserMiddleware(settings))
        observer.outer_middleware(MaintenanceMiddleware())
        observer.outer_middleware(ThrottleMiddleware(settings))

    dispatcher.include_router(start.router)
    dispatcher.include_router(browse.router)
    dispatcher.include_router(posts.router)
    dispatcher.include_router(account.router)
    dispatcher.include_router(admin_router)
    dispatcher.include_router(errors.router)
    dispatcher.include_router(fallback.router)
    return dispatcher