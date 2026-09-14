from aiogram import Dispatcher
from bot.handlers import start,browse,posts,account,admin,fallback
from bot.middlewares.ctele import CTeleMiddleware
from bot.middlewares.db import DatabaseMiddleware
from bot.middlewares.user import UserMiddleware
from bot.middlewares.throttle import ThrottleMiddleware


def build_dispatcher():
    dp = Dispatcher()
    dp.update.outer_middleware(ThrottleMiddleware())
    dp.update.outer_middleware(DatabaseMiddleware())
    dp.update.outer_middleware(UserMiddleware())
    dp.update.outer_middleware(CTeleMiddleware())
    dp.include_router(start.router)
    dp.include_router(browse.router)
    dp.include_router(posts.router)
    dp.include_router(account.router)
    dp.include_router(admin.router)
    dp.include_router(fallback.router)
    return dp
