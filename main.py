"""Entry point.

Run this from the project root:

    python start.py                # polling (default) + FastAPI on API_PORT
    python start.py --webhook      # webhook mode (needs WEBHOOK_BASE_URL)

FastAPI/uvicorn always serves the HTTP layer; in polling mode the aiogram
polling loop runs as an asyncio task inside the same event loop.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn  # noqa: E402

from bot.api.app import create_app  # noqa: E402
from bot.config import get_settings  # noqa: E402
from bot.utils.logger import register_secret, setup_logging  # noqa: E402

log = logging.getLogger("bot.startup")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CosplayTele Telegram bot")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--polling", action="store_true", help="force long-polling (default)")
    mode.add_argument("--webhook", action="store_true", help="force webhook mode")
    parser.add_argument("--host", help="override API_HOST")
    parser.add_argument("--port", type=int, help="override API_PORT")
    parser.add_argument("--log-level", help="override LOG_LEVEL")
    return parser.parse_args(argv)


async def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    settings = get_settings()
    if args.webhook:
        settings.run_mode = "webhook"
    elif args.polling:
        settings.run_mode = "polling"
    if args.host:
        settings.api_host = args.host
    if args.port:
        settings.api_port = args.port
    if args.log_level:
        settings.log_level = args.log_level

    setup_logging(settings.log_level, settings.log_dir)
    register_secret(settings.bot_token)

    problems = settings.validate_runtime()
    if problems:
        for problem in problems:
            log.error("configuration problem: %s", problem)
        log.error("see .env.example for the expected keys")
        return 1
    for warning in settings.warnings():
        log.warning("%s", warning)

    log.info(
        "starting | mode=%s | source=%s | auto-delete=%s | api=%s:%s",
        settings.run_mode,
        settings.source_base_url,
        f"{settings.auto_delete_ttl_minutes} min" if settings.auto_delete_enabled else "off",
        settings.api_host,
        settings.api_port,
    )

    app = create_app(settings)
    config = uvicorn.Config(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        access_log=False,
        loop="asyncio",
    )
    await uvicorn.Server(config).serve()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except KeyboardInterrupt:
        raise SystemExit(0)