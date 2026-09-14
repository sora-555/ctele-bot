"""Telegram webhook route, mounted only in webhook mode."""

from __future__ import annotations

import logging

from aiogram.types import Update
from fastapi import FastAPI, HTTPException, Request

from bot.config import Settings

log = logging.getLogger(__name__)

SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"


def register_webhook(app: FastAPI, settings: Settings) -> None:
    path = settings.webhook_path if settings.webhook_path.startswith("/") else f"/{settings.webhook_path}"

    @app.post(path, include_in_schema=False)
    async def telegram_webhook(request: Request) -> dict[str, bool]:
        if settings.webhook_secret:
            provided = request.headers.get(SECRET_HEADER)
            if provided != settings.webhook_secret:
                log.warning("rejected webhook call with a bad secret token")
                raise HTTPException(status_code=401, detail="invalid secret token")

        bot = request.app.state.bot
        dispatcher = request.app.state.dp
        payload = await request.json()
        update = Update.model_validate(payload, context={"bot": bot})
        await dispatcher.feed_update(bot, update)
        return {"ok": True}