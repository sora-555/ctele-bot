"""User list, search, detail cards and admin notes."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database import repository as repo
from bot.filters.admin import IsAdmin
from bot.handlers.common import show_screen
from bot.keyboards import admin as admin_kb
from bot.services.pagination import known
from bot.states.admin import UserNote, UserSearch
from bot.texts import ui
from bot.utils.text import truncate
from bot.utils.time import format_dt

router = Router(name="admin-users")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

PAGE_SIZE = 10
LEGEND = f"{ui.IMPORTANT} active {ui.KV} {ui.PENDING} blocked {ui.KV} {ui.SUCCESS} admin"


def _page_from(text: str | None, default: int = 1) -> int:
    for token in (text or "").split()[1:]:
        if token.isdigit():
            return max(int(token), 1)
    return default


async def send_user_card(
    bot, chat_id: int, session, target_id: int, *, edit_id: int | None = None
) -> bool:
    user = await repo.get(session, target_id)
    if user is None:
        await show_screen(
            bot,
            chat_id,
            text=(f"{ui.PENDING} 𝗨𝘀𝗲𝗿 𝗡𝗼𝘁 𝗙𝗼𝘂𝗻𝗱\n\n{ui.SEPARATOR}\n\n"
                  f"{ui.ITEM} ID {ui.KV} {target_id}\n\n{ui.SEPARATOR}"),
            markup=admin_kb.back_to_admin(),
            edit_id=edit_id,
        )
        return False

    favorites = await repo.count_favorites(session, user.id)
    notes = await repo.count_notes(session, user.id)
    blocks, _ = await repo.list_blocks_page(session, page=1, per_page=100, active_only=False)
    own_blocks = sum(1 for row in blocks if row.user_id == user.id)
    active = await repo.active_block(session, user.id)

    await show_screen(
        bot,
        chat_id,
        text=ui.user_card(
            user=user, favorites=favorites, blocks=own_blocks, notes=notes, active_block=active
        ),
        markup=admin_kb.user_card(user.id, is_blocked=not user.is_active, notes=notes),
        edit_id=edit_id,
    )
    return True


async def send_users(
    bot, chat_id: int, session, page: int, *, edit_id: int | None = None
) -> None:
    rows, total = await repo.list_page(session, page=page, per_page=PAGE_SIZE)
    info = known(total, PAGE_SIZE, page)
    if not rows:
        await show_screen(
            bot,
            chat_id,
            text=f"{ui.PENDING} 𝗡𝗼 𝗨𝘀𝗲𝗿𝘀\n\n{ui.SEPARATOR}\n\n{ui.ITEM} Nobody has started the bot yet\n",
            markup=admin_kb.back_to_admin(),
            edit_id=edit_id,
        )
        return
    admin_ids = set(await repo.all_ids(session))
    entries = [
        (
            user.id,
            f"{ui.SUCCESS}" if user.id in admin_ids else (f"{ui.IMPORTANT}" if user.is_active else f"{ui.PENDING}"),
        )
        for user in rows
    ]
    await show_screen(
        bot,
        chat_id,
        text=ui.users_list(total=total, page_label=info.label, legend=LEGEND),
        markup=admin_kb.users_list("", info, entries),
        edit_id=edit_id,
    )


@router.message(Command("users"))
async def cmd_users(message: Message, session) -> None:
    await send_users(message.bot, message.chat.id, session, _page_from(message.text))


@router.callback_query(F.data.startswith("a:users:"))
async def cb_users(callback: CallbackQuery, session) -> None:
    page = int(callback.data.split(":")[2])
    await callback.answer()
    await send_users(
        callback.bot, callback.message.chat.id, session, page, edit_id=callback.message.message_id
    )


@router.message(Command("find"))
async def cmd_find(message: Message, state: FSMContext) -> None:
    await state.set_state(UserSearch.query)
    await message.answer(ui.find_prompt())


@router.callback_query(F.data == "a:find")
async def cb_find(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(UserSearch.query)
    await callback.answer()
    await callback.message.answer(ui.find_prompt())


@router.message(StateFilter(UserSearch.query), F.text)
async def find_input(message: Message, state: FSMContext, session) -> None:
    query = (message.text or "").strip()
    await state.clear()
    matches = await repo.search(session, query, limit=10)
    if not matches:
        await message.answer(
            f"{ui.PENDING} 𝗡𝗼 𝗠𝗮𝘁𝗰𝗵𝗲𝘀\n\n{ui.SEPARATOR}\n\n"
            f"{ui.ITEM} Query {ui.KV} {truncate(query, 40)}\n\n{ui.SEPARATOR}",
            reply_markup=admin_kb.back_to_admin(),
        )
        return
    await message.answer(
        ui.find_results(query, len(matches)),
        reply_markup=admin_kb.find_results(
            [(user.id, f"{user.id} {ui.KV} {user.display_name}") for user in matches]
        ),
    )


@router.message(Command("user"))
async def cmd_user(message: Message, session) -> None:
    tokens = (message.text or "").split()
    if len(tokens) < 2 or not tokens[1].lstrip("-").isdigit():
        await message.answer(
            f"{ui.PENDING} 𝗨𝘀𝗲𝗿\n\n{ui.SEPARATOR}\n\n{ui.ITEM} Usage {ui.KV} /user <id>\n"
        )
        return
    await send_user_card(message.bot, message.chat.id, session, int(tokens[1]))


@router.callback_query(F.data.startswith("a:user:"))
async def cb_user(callback: CallbackQuery, session) -> None:
    target_id = int(callback.data.split(":")[2])
    await callback.answer()
    await send_user_card(
        callback.bot,
        callback.message.chat.id,
        session,
        target_id,
        edit_id=callback.message.message_id,
    )


@router.message(Command("note"))
async def cmd_note(message: Message, session, user) -> None:
    tokens = (message.text or "").split(maxsplit=2)
    if len(tokens) < 3 or not tokens[1].lstrip("-").isdigit():
        await message.answer(
            f"{ui.PENDING} 𝗡𝗼𝘁𝗲\n\n{ui.SEPARATOR}\n\n{ui.ITEM} Usage {ui.KV} /note <id> <text>\n"
        )
        return
    target_id = int(tokens[1])
    await repo.add_note(session, user_id=target_id, admin_id=user.id, text=tokens[2])
    await repo.log_action(
        session, admin_id=user.id, action="note", target_type="user", target_id=target_id
    )
    await message.answer(f"{ui.SUCCESS} 𝗡𝗼𝘁𝗲 𝗔𝗱𝗱𝗲𝗱")
    await send_user_card(message.bot, message.chat.id, session, target_id)


@router.callback_query(F.data.startswith("a:note:"))
async def cb_note(callback: CallbackQuery, state: FSMContext) -> None:
    target_id = int(callback.data.split(":")[2])
    await state.set_state(UserNote.text)
    await state.update_data(target_id=target_id)
    await callback.answer()
    await callback.message.answer(
        f"{ui.ACCENT} 𝗔𝗱𝗱 𝗡𝗼𝘁𝗲\n\n{ui.SEPARATOR}\n\n"
        f"{ui.ITEM} User {ui.KV} {target_id}\n"
        f"{ui.ITEM} Cancel {ui.KV} /cancel\n\n{ui.SEPARATOR}"
    )


@router.message(StateFilter(UserNote.text), F.text)
async def note_input(message: Message, state: FSMContext, session, user) -> None:
    data = await state.get_data()
    target_id = int(data.get("target_id") or 0)
    text = (message.text or "").strip()
    await state.clear()
    if not target_id or not text:
        await message.answer(f"{ui.PENDING} 𝗖𝗮𝗻𝗰𝗲𝗹𝗹𝗲𝗱")
        return
    await repo.add_note(session, user_id=target_id, admin_id=user.id, text=text)
    await repo.log_action(
        session, admin_id=user.id, action="note", target_type="user", target_id=target_id
    )
    await message.answer(f"{ui.SUCCESS} 𝗡𝗼𝘁𝗲 𝗔𝗱𝗱𝗲𝗱")
    await send_user_card(message.bot, message.chat.id, session, target_id)


async def _list_notes(
    bot, chat_id: int, session, target_id: int, *, edit_id: int | None = None
) -> None:
    notes = await repo.list_notes(session, target_id, limit=20)
    if not notes:
        await show_screen(
            bot,
            chat_id,
            text=(f"{ui.PENDING} 𝗡𝗼 𝗡𝗼𝘁𝗲𝘀\n\n{ui.SEPARATOR}\n\n"
                  f"{ui.ITEM} User {ui.KV} {target_id}\n\n{ui.SEPARATOR}"),
            markup=admin_kb.back_to_admin(),
            edit_id=edit_id,
        )
        return
    body = "\n".join(
        f"{ui.ITEM} {format_dt(note.created_at)} {ui.KV} {truncate(note.text, 60)}" for note in notes
    )
    await show_screen(
        bot,
        chat_id,
        text=(f"{ui.HEADER} 𝗡𝗼𝘁𝗲𝘀\n\n{ui.SEPARATOR}\n\n"
              f"{ui.ITEM} User {ui.KV} {target_id}\n"
              f"{ui.ITEM} Count {ui.KV} {len(notes)}\n\n{body}\n\n{ui.SEPARATOR}"),
        markup=admin_kb.back_to_admin(),
        edit_id=edit_id,
    )


@router.message(Command("notes"))
async def cmd_notes(message: Message, session) -> None:
    tokens = (message.text or "").split()
    if len(tokens) < 2 or not tokens[1].lstrip("-").isdigit():
        await message.answer(f"{ui.PENDING} 𝗡𝗼𝘁𝗲𝘀\n\n{ui.SEPARATOR}\n\n{ui.ITEM} Usage {ui.KV} /notes <id>\n")
        return
    await _list_notes(message.bot, message.chat.id, session, int(tokens[1]))


@router.callback_query(F.data.startswith("a:notes:"))
async def cb_notes(callback: CallbackQuery, session) -> None:
    target_id = int(callback.data.split(":")[2])
    await callback.answer()
    await _list_notes(
        callback.bot,
        callback.message.chat.id,
        session,
        target_id,
        edit_id=callback.message.message_id,
    )
