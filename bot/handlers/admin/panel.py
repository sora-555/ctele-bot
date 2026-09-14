"""Admin hub, global stats, health, cache reload and maintenance mode."""

from __future__ import annotations

from datetime import datetime, time, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from bot import __version__
from bot.database import repository as repo
from bot.database.base import database_size_bytes
from bot.database.models import Meta
from bot.filters.admin import IsAdmin, RoleAtLeast
from bot.handlers.common import show_screen
from bot.keyboards import admin as admin_kb
from bot.loader import services
from bot.texts import ui
from bot.utils.time import humanize_uptime, utcnow


def day_start() -> datetime:
    return datetime.combine(utcnow().date(), time.min)


async def send_panel(bot, chat_id: int, session, *, edit_id: int | None = None) -> None:
    svc = services()
    cache = await repo.cache_stats(session)
    text = ui.admin_panel(
        users=await repo.count_all(session),
        active_24h=await repo.count_active_since(session, utcnow() - timedelta(hours=24)),
        blocked=await repo.count_blocked(session),
        new_today=await repo.count_new_since(session, day_start()),
        mode=svc.settings.run_mode,
        source_ok=svc.ctele.last_error is None,
        cache_hits=cache.get("hits", 0),
    )
    await show_screen(
        bot,
        chat_id,
        text=text,
        markup=admin_kb.panel(source_ok=svc.ctele.last_error is None),
        edit_id=edit_id,
    )


async def send_global_stats(bot, chat_id: int, session, *, edit_id: int | None = None) -> None:
    await show_screen(
        bot,
        chat_id,
        text=ui.global_stats(
            totals=await repo.stats.totals(session),
            users={
                "total": await repo.count_all(session),
                "new_today": await repo.count_new_since(session, day_start()),
                "active_24h": await repo.count_active_since(session, utcnow() - timedelta(hours=24)),
                "blocked": await repo.count_blocked(session),
            },
            views=await repo.count_all_history(session),
            favorites=await repo.count_all_favorites(session),
        ),
        markup=admin_kb.back_to_admin(),
        edit_id=edit_id,
    )


async def send_health(bot, chat_id: int, session, *, edit_id: int | None = None) -> None:
    svc = services()
    ok, latency, _ = await svc.ctele.health()
    await show_screen(
        bot,
        chat_id,
        text=ui.health_text(
            mode=svc.settings.run_mode,
            uptime=humanize_uptime(svc.started_at),
            version=__version__,
            source_ok=ok,
            latency=latency,
            cache=await repo.cache_stats(session),
            db_bytes=database_size_bytes(),
            sessions=svc.sessions.count(),
            pending_deletions=await repo.count_deletions(session),
            ttl_label=svc.deletions.ttl_label,
        ),
        markup=admin_kb.health(),
        edit_id=edit_id,
    )


async def set_maintenance(session, enabled: bool) -> None:
    row = await session.get(Meta, "maintenance")
    value = "true" if enabled else "false"
    if row is None:
        session.add(Meta(key="maintenance", value=value))
    else:
        row.value = value
    await session.flush()


router = Router(name="admin-panel")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(Command("admin"))
async def cmd_admin(message: Message, session) -> None:
    await send_panel(message.bot, message.chat.id, session)


@router.callback_query(F.data == "a:panel")
async def cb_panel(callback: CallbackQuery, session) -> None:
    await callback.answer()
    await send_panel(
        callback.bot, callback.message.chat.id, session, edit_id=callback.message.message_id
    )


@router.message(Command("astats"))
async def cmd_astats(message: Message, session) -> None:
    await send_global_stats(message.bot, message.chat.id, session)


@router.message(Command("health"))
async def cmd_health(message: Message, session) -> None:
    await send_health(message.bot, message.chat.id, session)


@router.callback_query(F.data == "a:health")
async def cb_health(callback: CallbackQuery, session) -> None:
    await callback.answer()
    await send_health(
        callback.bot, callback.message.chat.id, session, edit_id=callback.message.message_id
    )


@router.message(Command("reload"), RoleAtLeast("owner"))
async def cmd_reload(message: Message, session, user) -> None:
    svc = services()
    cleared = svc.ctele.clear_cache()
    await repo.clear(session)
    try:
        await svc.ctele.categories(refresh=True)
    except Exception:  # noqa: BLE001
        pass
    await repo.log_action(session, admin_id=user.id, action="reload", details={"listing_keys": cleared})
    await message.answer(
        f"{ui.SUCCESS} 𝗖𝗮𝗰𝗵𝗲𝘀 𝗥𝗲𝗹𝗼𝗮𝗱𝗲𝗱\n\n{ui.SEPARATOR}\n\n"
        f"{ui.ITEM} Listing entries {ui.KV} {cleared} cleared\n"
        f"{ui.ITEM} Post cache {ui.KV} emptied\n"
        f"{ui.ITEM} Taxonomy {ui.KV} re-synced\n\n{ui.SEPARATOR}",
        reply_markup=admin_kb.reload_done(),
    )


@router.callback_query(F.data == "a:reload", RoleAtLeast("owner"))
async def cb_reload(callback: CallbackQuery, session, user) -> None:
    await callback.answer(f"{ui.SUCCESS} Reloaded")
    cleared = services().ctele.clear_cache()
    await repo.clear(session)
    await repo.log_action(session, admin_id=user.id, action="reload", details={"listing_keys": cleared})
    await show_screen(
        callback.bot,
        callback.message.chat.id,
        text=(f"{ui.SUCCESS} 𝗖𝗮𝗰𝗵𝗲𝘀 𝗥𝗲𝗹𝗼𝗮𝗱𝗲𝗱\n\n{ui.SEPARATOR}\n\n"
              f"{ui.ITEM} Listing entries {ui.KV} {cleared} cleared\n\n{ui.SEPARATOR}"),
        markup=admin_kb.reload_done(),
        edit_id=callback.message.message_id,
    )


@router.message(Command("maintenance"), RoleAtLeast("owner"))
async def cmd_maintenance(message: Message, session, user) -> None:
    args = (message.text or "").split()
    wanted = args[1].lower() if len(args) > 1 else None
    svc = services()
    if wanted in ("on", "off"):
        enabled = wanted == "on"
        svc.maintenance_enabled = enabled
        await set_maintenance(session, enabled)
        await repo.log_action(session, admin_id=user.id, action="maintenance", details={"enabled": enabled})
    state = f"{ui.IMPORTANT} On" if svc.maintenance_enabled else f"{ui.PENDING} Off"
    await message.answer(
        f"{ui.HEADER} 𝗠𝗮𝗶𝗻𝘁𝗲𝗻𝗮𝗻𝗰𝗲\n\n{ui.SEPARATOR}\n\n"
        f"{ui.ITEM} State {ui.KV} {state}\n"
        f"{ui.ITEM} Effect {ui.KV} non-admins are paused\n\n{ui.SEPARATOR}",
        reply_markup=admin_kb.maintenance(svc.maintenance_enabled),
    )


@router.callback_query(F.data == "a:maintoggle", RoleAtLeast("owner"))
async def cb_maintenance(callback: CallbackQuery, session, user) -> None:
    svc = services()
    svc.maintenance_enabled = not svc.maintenance_enabled
    await set_maintenance(session, svc.maintenance_enabled)
    await repo.log_action(
        session, admin_id=user.id, action="maintenance", details={"enabled": svc.maintenance_enabled}
    )
    state = f"{ui.IMPORTANT} On" if svc.maintenance_enabled else f"{ui.PENDING} Off"
    await callback.answer(f"Maintenance {state}")
    await show_screen(
        callback.bot,
        callback.message.chat.id,
        text=(f"{ui.HEADER} 𝗠𝗮𝗶𝗻𝘁𝗲𝗻𝗮𝗻𝗰𝗲\n\n{ui.SEPARATOR}\n\n"
              f"{ui.ITEM} State {ui.KV} {state}\n\n{ui.SEPARATOR}"),
        markup=admin_kb.maintenance(svc.maintenance_enabled),
        edit_id=callback.message.message_id,
    )
