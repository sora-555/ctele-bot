"""Role management. Owner-only, and the last owner can never be removed."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import repository as repo
from bot.database.models import ROLES, ROLE_OWNER
from bot.filters.admin import IsOwner
from bot.handlers.common import mirror_action, show_screen
from bot.keyboards import admin as admin_kb
from bot.states.admin import AddAdmin
from bot.texts import ui

router = Router(name="admin-roles")
router.message.filter(IsOwner())
router.callback_query.filter(IsOwner())

ROLE_MARKS = {ROLE_OWNER: ui.IMPORTANT, "admin": ui.IMPORTANT, "moderator": ui.PENDING}


async def send_admins(bot, chat_id: int, session, *, edit_id: int | None = None) -> None:
    rows = await repo.list_all(session)
    counts = await repo.count_by_role(session)
    body = [f"{row.user_id} {ui.KV} {ROLE_MARKS.get(row.role, ui.PENDING)} {row.role}" for row in rows]
    await show_screen(
        bot, chat_id, text=ui.admins_text(counts, body), markup=admin_kb.admins(), edit_id=edit_id
    )


@router.message(Command("admins"))
async def cmd_admins(message: Message, session) -> None:
    await send_admins(message.bot, message.chat.id, session)


@router.message(Command("addadmin"))
async def cmd_addadmin(message: Message, session, user) -> None:
    tokens = (message.text or "").split()[1:]
    if not tokens or not tokens[0].lstrip("-").isdigit():
        await message.answer(
            f"{ui.PENDING} 𝗔𝗱𝗱 𝗔𝗱𝗺𝗶𝗻\n\n{ui.SEPARATOR}\n\n"
            f"{ui.ITEM} Usage {ui.KV} /addadmin <id> [admin|moderator|owner]\n"
        )
        return
    target_id = int(tokens[0])
    role = tokens[1].lower() if len(tokens) > 1 and tokens[1].lower() in ROLES else "admin"
    await repo.grant(session, user_id=target_id, role=role, granted_by=user.id)
    await repo.log_action(
        session, admin_id=user.id, action="grant_role", target_type="user", target_id=target_id, details={"role": role}
    )
    await mirror_action(callback_bot(message), action=f"grant-{role}", target=str(target_id), admin_id=user.id)
    await message.answer(
        f"{ui.SUCCESS} 𝗥𝗼𝗹𝗲 𝗚𝗿𝗮𝗻𝘁𝗲𝗱\n\n{ui.SEPARATOR}\n\n"
        f"{ui.ITEM} User {ui.KV} {target_id}\n{ui.ITEM} Role {ui.KV} {role}\n\n{ui.SEPARATOR}",
        reply_markup=admin_kb.back_to_admin(),
    )
    await send_admins(message.bot, message.chat.id, session)


def callback_bot(message: Message):
    return message.bot


@router.message(Command("deladmin"))
async def cmd_deladmin(message: Message, session, user) -> None:
    tokens = (message.text or "").split()[1:]
    if not tokens or not tokens[0].lstrip("-").isdigit():
        await message.answer(f"{ui.PENDING} 𝗥𝗲𝗺𝗼𝘃𝗲 𝗔𝗱𝗺𝗶𝗻\n\n{ui.SEPARATOR}\n\n{ui.ITEM} Usage {ui.KV} /deladmin <id>\n")
        return
    await _revoke(message.bot, message.chat.id, session, user, int(tokens[0]))


async def _revoke(bot, chat_id: int, session, admin, target_id: int) -> None:
    role = await repo.get_role(session, target_id)
    if role is None:
        await bot.send_message(chat_id, f"{ui.PENDING} 𝗡𝗼𝘁 𝗮𝗻 𝗔𝗱𝗺𝗶𝗻\n\n{ui.SEPARATOR}\n\n{ui.ITEM} User {ui.KV} {target_id}\n")
        return
    if role == ROLE_OWNER and len(await repo.owners(session)) <= 1:
        await bot.send_message(
            chat_id,
            f"{ui.IMPORTANT} 𝗟𝗮𝘀𝘁 𝗢𝘄𝗻𝗲𝗿\n\n{ui.SEPARATOR}\n\n"
            f"{ui.ITEM} Reason {ui.KV} an owner must always remain\n"
            f"{ui.ITEM} Fix {ui.KV} promote someone else first\n\n{ui.SEPARATOR}",
        )
        return

    await repo.revoke(session, target_id)
    await repo.log_action(
        session, admin_id=admin.id, action="revoke_role", target_type="user", target_id=target_id, details={"role": role}
    )
    await mirror_action(bot, action="revoke-role", target=str(target_id), admin_id=admin.id)
    await bot.send_message(
        chat_id,
        f"{ui.SUCCESS} 𝗥𝗼𝗹𝗲 𝗥𝗲𝘃𝗼𝗸𝗲𝗱\n\n{ui.SEPARATOR}\n\n"
        f"{ui.ITEM} User {ui.KV} {target_id}\n{ui.ITEM} Previous {ui.KV} {role}\n\n{ui.SEPARATOR}",
        reply_markup=admin_kb.back_to_admin(),
    )
    await send_admins(bot, chat_id, session)


@router.callback_query(F.data == "a:addadmin")
async def cb_addadmin(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddAdmin.user_id)
    await state.update_data(mode="add")
    await callback.answer()
    await callback.message.answer(
        f"{ui.ACCENT} 𝗔𝗱𝗱 𝗔𝗱𝗺𝗶𝗻\n\n{ui.SEPARATOR}\n\n"
        f"{ui.ITEM} Send the Telegram ID to promote\n"
        f"{ui.ITEM} Cancel {ui.KV} /cancel\n\n{ui.SEPARATOR}"
    )


@router.callback_query(F.data == "a:deladminprompt")
async def cb_deladmin_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddAdmin.user_id)
    await state.update_data(mode="remove")
    await callback.answer()
    await callback.message.answer(
        f"{ui.ACCENT} 𝗥𝗲𝗺𝗼𝘃𝗲 𝗔𝗱𝗺𝗶𝗻\n\n{ui.SEPARATOR}\n\n"
        f"{ui.ITEM} Send the Telegram ID to demote\n"
        f"{ui.ITEM} Cancel {ui.KV} /cancel\n\n{ui.SEPARATOR}"
    )


@router.message(StateFilter(AddAdmin.user_id))
async def addadmin_input(message: Message, state: FSMContext, session, user) -> None:
    data = await state.get_data()
    mode = data.get("mode", "add")
    raw = (message.text or "").strip()
    if not raw.lstrip("-").isdigit():
        await message.answer(
            f"{ui.PENDING} 𝗘𝘅𝗽𝗲𝗰𝘁𝗲𝗱 𝗮𝗻 𝗜𝗗\n\n{ui.SEPARATOR}\n\n"
            f"{ui.ITEM} Send {ui.KV} a numeric Telegram ID\n"
            f"{ui.ITEM} Cancel {ui.KV} /cancel\n"
        )
        return

    target_id = int(raw)
    if mode == "remove":
        await state.clear()
        await _revoke(message.bot, message.chat.id, session, user, target_id)
        return

    await state.update_data(target_id=target_id)
    await state.set_state(AddAdmin.role)
    await message.answer(
        f"{ui.ACCENT} 𝗣𝗶𝗰𝗸 𝗮 𝗥𝗼𝗹𝗲\n\n{ui.SEPARATOR}\n\n"
        f"{ui.ITEM} User {ui.KV} {target_id}\n",
        reply_markup=admin_kb.role_picker(target_id),
    )


@router.callback_query(F.data.startswith("a:setrole:"), StateFilter(AddAdmin.role))
async def cb_set_role(callback: CallbackQuery, state: FSMContext, session, user) -> None:
    _, _, raw_id, role = callback.data.split(":")
    target_id = int(raw_id)
    if role not in ROLES:
        role = "admin"

    await state.clear()
    await repo.grant(session, user_id=target_id, role=role, granted_by=user.id)
    await repo.log_action(
        session, admin_id=user.id, action="grant_role", target_type="user", target_id=target_id, details={"role": role}
    )
    await callback.answer(f"{ui.SUCCESS} {role}")
    await mirror_action(callback.bot, action=f"grant-{role}", target=str(target_id), admin_id=user.id)
    await send_admins(
        callback.bot, callback.message.chat.id, session, edit_id=callback.message.message_id
    )
