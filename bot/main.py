from aiogram import Dispatcher

from bot.handlers import account, admin, broadcast, browse, errors, fallback, start, viewer
from bot.middlewares.access import AccessMiddleware
from bot.middlewares.ctele import CTeleMiddleware
from bot.middlewares.db import DatabaseMiddleware
from bot.middlewares.throttle import ThrottleMiddleware
from bot.middlewares.user import UserMiddleware


def build_dispatcher():
    dp = Dispatcher()
    dp.update.outer_middleware(ThrottleMiddleware())
    dp.update.outer_middleware(DatabaseMiddleware())
    dp.update.outer_middleware(UserMiddleware())
    dp.update.outer_middleware(AccessMiddleware())
    dp.update.outer_middleware(CTeleMiddleware())
    dp.errors.register(errors.handle_error)
    dp.include_router(start.router)
    dp.include_router(browse.router)
    dp.include_router(viewer.router)
    dp.include_router(account.router)
    dp.include_router(admin.router)
    dp.include_router(broadcast.router)
    dp.include_router(fallback.router)
    return dp
