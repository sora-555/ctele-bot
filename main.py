import asyncio,logging
from bot.config import settings
from bot.database.base import init_db
from bot.loader import bot
from bot.main import build_dispatcher
from bot.commands import register_commands
from bot.api.app import create_app
async def run():
 if not settings.bot_token: raise RuntimeError('BOT_TOKEN is missing. Copy .env.example to .env and configure it.')
 await init_db(); dp=build_dispatcher(); await register_commands(bot)
 app=create_app(bot,dp,settings.webhook_secret)
 import uvicorn
 if settings.run_mode.lower()=='webhook':
  if not settings.webhook_base_url: raise RuntimeError('WEBHOOK_BASE_URL is required in webhook mode')
  await bot.set_webhook(settings.webhook_base_url.rstrip('/')+settings.webhook_path,secret_token=settings.webhook_secret or None)
  await uvicorn.Server(uvicorn.Config(app,host=settings.api_host,port=settings.api_port)).serve()
 else:
  task=asyncio.create_task(uvicorn.Server(uvicorn.Config(app,host=settings.api_host,port=settings.api_port,log_level='warning')).serve())
  try: await dp.start_polling(bot)
  finally: task.cancel(); await bot.session.close()
if __name__=='__main__': logging.basicConfig(level=settings.log_level); asyncio.run(run())
