"""Automatic command menu registration.

The same menus BotFather would set by hand via `/setcommands` are registered
programmatically on every boot: a default scope for everyone, plus a per-chat
scope for each admin so their client shows the admin set as well. `/help` is
rendered from these same tables, so the two can never drift apart.
"""

from __future__ import annotations

import logging
import re

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import (
    BotCommand,
    BotCommandScopeChat,
    BotCommandScopeDefault,
    MenuButtonCommands,
)

from bot.config import Settings

log = logging.getLogger(__name__)

COMMAND_RE = re.compile(r"^[a-z0-9_]{1,32}$")
DESCRIPTION_LIMIT = 256

USER_COMMANDS: list[tuple[str, str]] = [
    ("start", "Start the bot"),
    ("menu", "Main menu"),
    ("help", "Command list"),
    ("latest", "Newest posts"),
    ("popular", "Trending posts"),
    ("search", "Search posts"),
    ("categories", "Browse categories"),
    ("category", "Open a category"),
    ("random", "Random post"),
    ("post", "Open a post link"),
    ("last", "Reopen the last post"),
    ("gallery", "Gallery of the last post"),
    ("favorites", "Saved posts"),
    ("history", "Recently viewed"),
    ("profile", "Your profile"),
    ("settings", "Preferences"),
    ("stats", "Your usage stats"),
    ("about", "Bot information"),
    ("ping", "Check latency"),
    ("cancel", "Cancel current input"),
]

ADMIN_COMMANDS: list[tuple[str, str]] = [
    ("admin", "Control panel"),
    ("astats", "Global statistics"),
    ("users", "User list"),
    ("find", "Search users"),
    ("user", "User detail"),
    ("note", "Add an internal note"),
    ("notes", "List notes for a user"),
    ("block", "Block a user"),
    ("unblock", "Unblock a user"),
    ("blocked", "Active blocks"),
    ("broadcast", "Message all users"),
    ("export", "Download a CSV"),
    ("logs", "Audit log"),
    ("health", "System health"),
    ("reload", "Clear caches"),
    ("maintenance", "Lock the bot"),
    ("admins", "Manage roles"),
    ("addadmin", "Grant a role"),
    ("deladmin", "Revoke a role"),
]


def validate(commands: list[tuple[str, str]], label: str) -> None:
    """Fail loudly at import time rather than silently on Telegram's side."""
    for name, description in commands:
        if not COMMAND_RE.match(name):
            raise ValueError(f"{label}: invalid command name {name!r}")
        if not description or len(description) > DESCRIPTION_LIMIT:
            raise ValueError(f"{label}: bad description for {name!r}")


validate(USER_COMMANDS, "USER_COMMANDS")
validate(ADMIN_COMMANDS, "ADMIN_COMMANDS")


def _as_objects(commands: list[tuple[str, str]]) -> list[BotCommand]:
    return [BotCommand(command=name, description=description) for name, description in commands]


def user_menu() -> list[BotCommand]:
    return _as_objects(USER_COMMANDS)


def admin_menu() -> list[BotCommand]:
    return _as_objects(USER_COMMANDS + ADMIN_COMMANDS)


def help_rows(admin: bool) -> list[tuple[str, str]]:
    return USER_COMMANDS + (ADMIN_COMMANDS if admin else [])


async def register_commands(bot: Bot, settings: Settings, *, admin_ids: list[int] | None = None) -> None:
    if not settings.set_commands_on_startup:
        return
    try:
        await bot.set_my_commands(user_menu(), scope=BotCommandScopeDefault())
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    except TelegramAPIError as exc:
        log.warning("could not register the default command menu: %s", exc)

    if not settings.command_scope_admins:
        return
    for admin_id in admin_ids or settings.owner_ids:
        await register_admin_scope(bot, admin_id)


async def register_admin_scope(bot: Bot, chat_id: int) -> bool:
    """Give one admin chat the extended menu. False when Telegram refuses."""
    try:
        await bot.set_my_commands(admin_menu(), scope=BotCommandScopeChat(chat_id=chat_id))
        return True
    except TelegramAPIError as exc:
        # Happens when the admin has never opened a chat with the bot.
        log.debug("admin scope for %s skipped: %s", chat_id, exc)
        return False


async def clear_admin_scope(bot: Bot, chat_id: int) -> None:
    try:
        await bot.delete_my_commands(scope=BotCommandScopeChat(chat_id=chat_id))
    except TelegramAPIError as exc:
        log.debug("could not clear scope for %s: %s", chat_id, exc)