from fastapi import FastAPI
from bot.api.health import router as health
def create_app(bot,dp,secret=''):
 app=FastAPI(title='CosplayTele Bot'); app.state.bot=bot; app.include_router(health)
 from bot.api.webhook import setup_webhook; setup_webhook(app.router,dp,secret); return app
