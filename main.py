import asyncio
import logging

from bot.api.app import create_app
from bot.commands import register_commands
from bot.config import settings
from bot.database.base import SessionLocal, init_db
from bot.database.repository import admins as admins_repo
from bot.loader import bot
from bot.middlewares.ctele import service as ctele_service
from bot.main import build_dispatcher
from bot.services.broadcast import engine
from bot.services.deletion import DeletionService
from bot.services.sessions import store, sweep_expired

log = logging.getLogger(__name__)


async def sweep_sessions():
    while True:
        await asyncio.sleep(300)
        try:
            async with SessionLocal() as session:
                removed = await sweep_expired(session)
                alive = await store.alive_ids(session)
                await session.commit()
            store.prune_locks(alive)
            if removed:
                log.info('swept %s expired sessions', removed)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception('session sweep failed')


async def run():
    if not settings.bot_token:
        raise RuntimeError('BOT_TOKEN is missing. Copy .env.example to .env and configure it.')
    await init_db()
    async with SessionLocal() as session:
        created = await admins_repo.bootstrap(session, settings.admin_id_list)
        await session.commit()
    if created:
        log.info('bootstrapped %s admin account(s)', created)

    dp = build_dispatcher()
    await register_commands(bot)

    deletion = DeletionService(bot)
    await deletion.start()
    resumed = await engine.resume_pending(bot)
    if resumed:
        log.info('resumed broadcasts: %s', resumed)

    app = create_app(bot, dp, settings.webhook_secret)
    import uvicorn

    try:
        if settings.run_mode.lower() == 'webhook':
            if not settings.webhook_base_url:
                raise RuntimeError('WEBHOOK_BASE_URL is required in webhook mode')
            await bot.set_webhook(
                settings.webhook_base_url.rstrip('/') + settings.webhook_path,
                secret_token=settings.webhook_secret or None,
                drop_pending_updates=settings.webhook_drop_pending,
            )
            await uvicorn.Server(uvicorn.Config(app, host=settings.api_host, port=settings.api_port)).serve()
        else:
            api = asyncio.create_task(
                uvicorn.Server(
                    uvicorn.Config(app, host=settings.api_host, port=settings.api_port, log_level='warning')
                ).serve()
            )
            sweeper = asyncio.create_task(sweep_sessions())
            try:
                await dp.start_polling(bot)
            finally:
                api.cancel()
                sweeper.cancel()
    finally:
        await deletion.stop()
        if settings.run_mode.lower() == 'webhook' and settings.webhook_delete_on_shutdown:
            try:
                await bot.delete_webhook(drop_pending_updates=True)
            except Exception:
                log.exception('could not delete the webhook')
        await ctele_service.close()
        await bot.session.close()


if __name__ == '__main__':
    logging.basicConfig(level=settings.log_level)
    asyncio.run(run())
