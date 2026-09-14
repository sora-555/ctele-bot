"""Blocking and unblocking users."""

from __future__ import annotations

from datetime import timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.database import repository as repo
from bot.filters.admin import IsAdmin, RoleAtLeast
from bot.handlers.admin.users import send_user_card
from bot.handlers.common import mirror_action, safe_edit_text, show_screen
from bot.keyboards import admin as admin_kb
from bot.keyboards import inline
from bot.loader import services
from bot.services.pagination import known
from bot.texts import ui
from bot.utils.time import utcnow

router = Router(name="admin-moderation")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

PAGE_SIZE = 8
DEFAULT_REASON = "manual block"


async def apply_block(session, *, target_id: int, admin_id: int, reason: str, until) -> bool:
    user = await repo.get(session, target_id)
    if user is None:
        return False
    await repo.set_blocked(
        session, target_id, is_active=False, reason=reason, admin_id=admin_id, until=until
    )
    await repo.create_block(
        session, user_id=target_id, admin_id=admin_id, reason=reason, expires_at=until
    )
    await repo.stats.touch(session, blocks=1)
    await repo.log_action(
        session,
        admin_id=admin_id,
        action="block",
        target_type="user",
        target_id=target_id,
        details={"reason": reason, "until": until.isoformat() if until else None},
    )
    return True


async def apply_unblock(session, *, target_id: int, admin_id: int) -> bool:
    user = await repo.get(session, target_id)
    if user is None:
        return False
    await repo.set_blocked(session, target_id, is_active=True)
    await repo.lift_blocks(session, user_id=target_id, admin_id=admin_id)
    await repo.log_action(
        session, admin_id=admin_id, action="unblock", target_type="user", target_id=target_id
    )
    return True


async def send_block_confirm(
    bot, chat_id: int, *, admin_id: int, target_id: int, reason: str, until, edit_id: int | None = None
) -> None:
    sid = services().sessions.new(
        {
            "user_id": admin_id,
            "kind": "block",
            "target": target_id,
            "reason": reason,
            "until": until,
        }
    )
    await show_screen(
        bot,
        chat_id,
        text=ui.block_confirm(
            user_id=target_id,
            handle=(await _handle(bot, target_id)) or "-",
            reason=reason,
            until=until.strftime("%Y-%m-%d %H:%M") if until else "permanent",
        ),
        markup=inline.confirm(
            f"a:blockok:{sid}", f"a:user:{target_id}", yes_label=f"{ui.IMPORTANT} Confirm Block"
        ),
        edit_id=edit_id,
    )


async def _handle(bot, target_id: int) -> str:
    from bot.database.base import session_scope

    async with session_scope() as session:
        user = await repo.get(session, target_id)
        return user.handle if user else "-"


@router.message(Command("block"), RoleAtLeast("admin"))
async def cmd_block(message: Message, session, user) -> None:
    tokens = (message.text or "").split()
    if len(tokens) < 2 or not tokens[1].lstrip("-").isdigit():
        await message.answer(
            f"{ui.PENDING} 𝗕𝗹𝗼𝗰𝗸\n\n{ui.SEPARATOR}\n\n"
            f"{ui.ITEM} Usage {ui.KV} /block <id> [reason] [--days N]\n"
        )
        return
    target_id = int(tokens[1])
    until = None
    reason_parts: list[str] = []
    index = 2
    while index < len(tokens):
        if tokens[index] == "--days" and index + 1 < len(tokens) and tokens[index + 1].isdigit():
            until = utcnow() + timedelta(days=int(tokens[index + 1]))
            index += 2
            continue
        reason_parts.append(tokens[index])
        index += 1
    reason = " ".join(reason_parts).strip() or DEFAULT_REASON
    await send_block_confirm(
        message.bot, message.chat.id, admin_id=user.id, target_id=target_id, reason=reason, until=until
    )


@router.callback_query(F.data.startswith("a:block:"), RoleAtLeast("admin"))
async def cb_block_ask(callback: CallbackQuery, user) -> None:
    target_id = int(callback.data.split(":")[2])
    await callback.answer()
    await send_block_confirm(
        callback.bot,
        callback.message.chat.id,
        admin_id=user.id,
        target_id=target_id,
        reason=DEFAULT_REASON,
        until=None,
        edit_id=callback.message.message_id,
    )


@router.callback_query(F.data.startswith("a:blockok:"), RoleAtLeast("admin"))
async def cb_block_confirm(callback: CallbackQuery, session, user) -> None:
    sid = callback.data.split(":")[2]
    payload = services().sessions.get(sid, user_id=user.id)
    if payload is None:
        await callback.answer("Expired", show_alert=True)
        return

    target_id = int(payload["target"])
    reason = payload.get("reason") or DEFAULT_REASON
    until = payload.get("until")

    applied = await apply_block(
        session, target_id=target_id, admin_id=user.id, reason=reason, until=until
    )
    if not applied:
        await callback.answer("User not found", show_alert=True)
        return

    services().sessions.drop(sid)
    await callback.answer(f"{ui.SUCCESS} Blocked")
    await mirror_action(
        callback.bot, action="block", target=str(target_id), admin_id=user.id, reason=reason
    )
    try:
        await safe_edit_text(
            callback.bot,
            callback.message.chat.id,
            callback.message.message_id,
            ui.block_done(user_id=target_id, admin_id=user.id, reason=reason),
            admin_kb.back_to_admin(),
        )
    except Exception:  # noqa: BLE001
        pass


@router.message(Command("unblock"), RoleAtLeast("admin"))
async def cmd_unblock(message: Message, session, user) -> None:
    tokens = (message.text or "").split()
    if len(tokens) < 2 or not tokens[1].lstrip("-").isdigit():
        await message.answer(f"{ui.PENDING} 𝗨𝗻𝗯𝗹𝗼𝗰𝗸\n\n{ui.SEPARATOR}\n\n{ui.ITEM} Usage {ui.KV} /unblock <id>\n")
        return
    target_id = int(tokens[1])
    if not await apply_unblock(session, target_id=target_id, admin_id=user.id):
        await message.answer(f"{ui.PENDING} 𝗨𝘀𝗲𝗿 𝗡𝗼𝘁 𝗙𝗼𝘂𝗻𝗱")
        return
    await mirror_action(callback_bot(message), action="unblock", target=str(target_id), admin_id=user.id)
    await message.answer(ui.unblock_done(target_id), reply_markup=admin_kb.back_to_admin())


def callback_bot(message: Message):
    return message.bot


@router.callback_query(F.data.startswith("a:unblock:"), RoleAtLeast("admin"))
async def cb_unblock(callback: CallbackQuery, session, user) -> None:
    target_id = int(callback.data.split(":")[2])
    if not await apply_unblock(session, target_id=target_id, admin_id=user.id):
        await callback.answer("User not found", show_alert=True)
        return
    await callback.answer(f"{ui.SUCCESS} Unblocked")
    await mirror_action(callback.bot, action="unblock", target=str(target_id), admin_id=user.id)
    # The refreshed card already shows the user back in the active state; the toast
    # carries the confirmation, so no second message is needed.
    await send_user_card(
        callback.bot,
        callback.message.chat.id,
        session,
        target_id,
        edit_id=callback.message.message_id,
    )


@router.message(Command("blocked"))
async def cmd_blocked(message: Message, session) -> None:
    await send_blocked(message.bot, message.chat.id, session, page=1)


@router.callback_query(F.data.startswith("a:blocked:"))
async def cb_blocked(callback: CallbackQuery, session) -> None:
    page = int(callback.data.split(":")[2])
    await callback.answer()
    await send_blocked(
        callback.bot, callback.message.chat.id, session, page, edit_id=callback.message.message_id
    )


async def send_blocked(
    bot, chat_id: int, session, page: int, *, edit_id: int | None = None
) -> None:
    rows, total = await repo.list_blocks_page(session, page=page, per_page=PAGE_SIZE, active_only=True)
    info = known(total, PAGE_SIZE, page)
    if not rows:
        await show_screen(
            bot,
            chat_id,
            text=f"{ui.PENDING} 𝗡𝗼 𝗕𝗹𝗼𝗰𝗸𝘀\n\n{ui.SEPARATOR}\n\n{ui.ITEM} Nobody is blocked\n",
            markup=admin_kb.back_to_admin(),
            edit_id=edit_id,
        )
        return
    entries = [(row.user_id, row.reason or "no reason") for row in rows]
    await show_screen(
        bot,
        chat_id,
        text=ui.blocked_list(total, info.label),
        markup=admin_kb.blocked_list("", info, entries),
        edit_id=edit_id,
    )
