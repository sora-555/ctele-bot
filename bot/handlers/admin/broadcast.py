"""Broadcast: draft -> preview -> rate-limited fan-out with live progress."""

from __future__ import annotations

import asyncio
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import repository as repo
from bot.database.base import session_scope
from bot.database.models import Broadcast
from bot.filters.admin import IsAdmin, RoleAtLeast
from bot.keyboards import admin as admin_kb
from bot.loader import services
from bot.states.admin import BroadcastFlow
from bot.texts import ui
from bot.utils.text import truncate
from bot.utils.time import utcnow

log = logging.getLogger(__name__)
router = Router(name="admin-broadcast")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

_TASKS: set[asyncio.Task] = set()


def _format_duration(seconds: int) -> str:
    minutes, rest = divmod(max(seconds, 0), 60)
    if minutes:
        return f"{minutes}m {rest:02d}s"
    return f"{rest}s"


async def _run_broadcast(
    bot,
    *,
    broadcast_id: int,
    recipients: list[int],
    text: str | None,
    photo: str | None,
    chat_id: int,
    message_id: int,
    admin_id: int,
) -> None:
    svc = services()
    started = utcnow()

    async def on_progress(sent: int, failed: int) -> None:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=ui.broadcast_progress(sent, failed, len(recipients)),
                reply_markup=admin_kb.broadcast_running(broadcast_id),
            )
        except TelegramAPIError:
            pass

    try:
        sent, failed, cancelled = await svc.broadcasts.run(
            broadcast_id=broadcast_id,
            recipients=recipients,
            text=text,
            photo=photo,
            on_progress=on_progress,
        )
    except Exception:  # noqa: BLE001
        log.exception("broadcast %s crashed", broadcast_id)
        sent = failed = 0
        cancelled = True

    duration = _format_duration(int((utcnow() - started).total_seconds()))

    async with session_scope() as session:
        row = await session.get(Broadcast, broadcast_id)
        if row is not None:
            row.sent_ok = sent
            row.sent_fail = failed
            row.status = "cancelled" if cancelled else "done"
            row.finished_at = utcnow()
        await repo.stats.touch(session, broadcasts=0 if cancelled else 1)
        await repo.log_action(
            session,
            admin_id=admin_id,
            action="broadcast",
            target_type="users",
            target_id=str(len(recipients)),
            details={"sent": sent, "failed": failed, "cancelled": cancelled},
        )

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=ui.broadcast_summary(
                sent=sent, failed=failed, cancelled=cancelled, duration=duration, admin_id=admin_id
            ),
            reply_markup=admin_kb.back_to_admin(),
        )
    except TelegramAPIError:
        pass
    svc.broadcasts.clear(broadcast_id)


@router.message(Command("broadcast"), RoleAtLeast("admin"))
async def cmd_broadcast(message: Message, state: FSMContext) -> None:
    await state.set_state(BroadcastFlow.content)
    await message.answer(ui.broadcast_prompt(), reply_markup=admin_kb.back_to_admin())


@router.callback_query(F.data == "a:broadcast", RoleAtLeast("admin"))
async def cb_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(BroadcastFlow.content)
    await callback.answer()
    await callback.message.answer(ui.broadcast_prompt())


@router.message(StateFilter(BroadcastFlow.content), RoleAtLeast("admin"))
async def broadcast_content(message: Message, state: FSMContext, session) -> None:
    text = message.text or message.caption
    photo = message.photo[-1].file_id if message.photo else None
    if not text and not photo:
        await message.answer(
            f"{ui.PENDING} 𝗨𝗻𝘀𝘂𝗽𝗽𝗼𝗿𝘁𝗲𝗱\n\n{ui.SEPARATOR}\n\n"
            f"{ui.ITEM} Send {ui.KV} text, or a photo with an optional caption\n"
        )
        return

    recipients = await repo.recipient_ids(session)
    await state.update_data(text=text, photo=photo)
    await state.set_state(BroadcastFlow.confirm)

    preview = text or "(photo without caption)"
    await message.answer(
        ui.broadcast_preview(
            audience=len(recipients), rate=services().settings.broadcast_rate, body=preview
        ),
        reply_markup=admin_kb.broadcast_preview(),
    )


@router.callback_query(F.data == "a:bcnope", RoleAtLeast("admin"))
async def cb_broadcast_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Cancelled")
    try:
        await callback.message.edit_text(
            f"{ui.PENDING} 𝗕𝗿𝗼𝗮𝗱𝗰𝗮𝘀𝘁 𝗖𝗮𝗻𝗰𝗲𝗹𝗹𝗲𝗱\n\n{ui.SEPARATOR}\n\n"
            f"{ui.ITEM} Nothing was sent\n",
            reply_markup=admin_kb.back_to_admin(),
        )
    except TelegramAPIError:
        pass


@router.callback_query(F.data == "a:bcok", RoleAtLeast("admin"))
async def cb_broadcast_send(callback: CallbackQuery, state: FSMContext, session, user) -> None:
    data = await state.get_data()
    await state.clear()
    text = data.get("text")
    photo = data.get("photo")

    recipients = await repo.recipient_ids(session)
    if not recipients:
        await callback.answer("No recipients", show_alert=True)
        return

    record = Broadcast(
        admin_id=user.id,
        kind="photo" if photo else "text",
        content=truncate(text or "", 4000) or None,
        file_id=photo,
        status="running",
        total=len(recipients),
        started_at=utcnow(),
    )
    session.add(record)
    await session.flush()
    broadcast_id = record.id
    await repo.log_action(
        session, admin_id=user.id, action="broadcast_start", target_type="users", target_id=str(len(recipients))
    )

    await callback.answer("Sending")
    progress = await callback.message.answer(
        ui.broadcast_progress(0, 0, len(recipients)),
        reply_markup=admin_kb.broadcast_running(broadcast_id),
    )

    task = asyncio.create_task(
        _run_broadcast(
            callback.bot,
            broadcast_id=broadcast_id,
            recipients=recipients,
            text=text,
            photo=photo,
            chat_id=progress.chat.id,
            message_id=progress.message_id,
            admin_id=user.id,
        )
    )
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)


@router.callback_query(F.data.startswith("a:bccancel:"), RoleAtLeast("admin"))
async def cb_broadcast_abort(callback: CallbackQuery) -> None:
    broadcast_id = int(callback.data.split(":")[2])
    services().broadcasts.cancel(broadcast_id)
    await callback.answer("Stopping after the current message")
