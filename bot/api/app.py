"""FastAPI application factory and the process lifecycle.

FastAPI/uvicorn is always the HTTP layer. In the default polling mode the
aiogram polling loop runs as an asyncio task inside the same event loop; in
webhook mode Telegram drives a FastAPI route instead.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from fastapi import FastAPI

from bot import __version__
from bot.api import health
from bot.api.webhook import register_webhook
from bot.commands import register_commands
from bot.config import Settings, get_settings
from bot.database import repository as repo
from bot.database.base import dispose_db, init_db, session_scope
from bot.database.models import Meta
from bot.handlers.common import mirror_to_log_channel
from bot.loader import Services, init_services, reset_services
from bot.main import build_dispatcher
from bot.texts import ui
from bot.utils.time import utcnow

log = logging.getLogger(__name__)


async def _bootstrap_admins(settings: Settings) -> None:
    if not settings.owner_ids:
        return
    async with session_scope() as session:
        added = await repo.bootstrap(session, settings.owner_ids)
    if added:
        log.info("bootstrapped %s admin(s) from ADMIN_IDS", added)


async def _read_maintenance() -> bool:
    async with session_scope() as session:
        row = await session.get(Meta, "maintenance")
    return bool(row and (row.value or "").lower() == "true")


async def _poll(bot: Bot, dispatcher: Dispatcher) -> None:
    try:
        # Verify reachability and credentials inside our own supervised task. aiogram
        # runs the long-poll loop in an internal task whose exception nobody retrieves,
        # so a bad token or a dead network would otherwise leave the process running
        # (and /healthz green) while it never actually polls.
        me = await bot.me()
        log.info("polling as @%s (%s)", me.username, me.id)
        await dispatcher.start_polling(
            bot,
            handle_signals=False,
            close_bot_session=False,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 - report and re-raise so it is visible
        log.exception("polling stopped unexpectedly")
        await mirror_to_log_channel(
            bot,
            ui.mirror_error(where="polling task", kind=type(exc).__name__, user_id=None, when=utcnow()),
        )
        raise


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        bot = Bot(
            token=resolved.bot_token,
            default=DefaultBotProperties(
                parse_mode=ParseMode.HTML, link_preview_is_disabled=True
            ),
        )
        dispatcher = build_dispatcher(resolved)
        app.state.bot = bot
        app.state.dp = dispatcher

        await init_db()
        await _bootstrap_admins(resolved)

        svc: Services = init_services(bot, resolved)
        svc.maintenance_enabled = await _read_maintenance()
        svc.deletions.start()

        if resolved.set_commands_on_startup:
            async with session_scope() as session:
                admin_ids = await repo.all_ids(session)
            await register_commands(bot, resolved, admin_ids=admin_ids)

        polling_task: asyncio.Task | None = None
        if resolved.is_webhook:
            await bot.set_webhook(
                url=resolved.webhook_url,
                secret_token=resolved.webhook_secret or None,
                drop_pending_updates=resolved.webhook_drop_pending,
                allowed_updates=dispatcher.resolve_used_update_types(),
            )
            log.info("webhook mode: route %s", resolved.webhook_path)
        else:
            polling_task = asyncio.create_task(_poll(bot, dispatcher), name="aiogram-polling")
            log.info("polling mode: FastAPI on %s:%s", resolved.api_host, resolved.api_port)

        try:
            yield
        finally:
            if polling_task is not None:
                polling_task.cancel()
                with contextlib.suppress(BaseException):
                    await polling_task
            with contextlib.suppress(Exception):
                await svc.deletions.stop()
            if resolved.is_webhook and resolved.webhook_delete_on_shutdown:
                with contextlib.suppress(TelegramAPIError):
                    await bot.delete_webhook(drop_pending_updates=False)
            with contextlib.suppress(Exception):
                await svc.ctele.close()
            with contextlib.suppress(Exception):
                await bot.session.close()
            with contextlib.suppress(Exception):
                await dispose_db()
            reset_services()
            log.info("shutdown complete")

    app = FastAPI(
        title="CosplayTele Bot",
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = resolved
    app.include_router(health.router)
    if resolved.is_webhook:
        register_webhook(app, resolved)
    return app
