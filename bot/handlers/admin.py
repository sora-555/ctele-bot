import csv
import io
import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from bot.config import settings
from bot.database.repository import admins as admins_repo
from bot.database.repository import content as content_repo
from bot.database.repository import stats as stats_repo
from bot.database.repository import users as users_repo
from bot.handlers import viewer
from bot.keyboards.inline import admin_back_kb, admin_kb, user_card_kb, users_list_kb
from bot.services.pagination import page_count
from bot.states.user import AdminFlow
from bot.texts import symbols as S
from bot.texts import ui

log = logging.getLogger(__name__)
router = Router()

PAGE_SIZE = 8
LAST_QUERY: dict[int, str] = {}


async def guard(event, db) -> bool:
    if await admins_repo.is_admin(db, event.from_user.id):
        return True
    if isinstance(event, CallbackQuery):
        await event.answer('Admins only.', show_alert=True)
    else:
        await event.answer('That command is restricted to admins.')
    return False


async def admin_screen(db):
    stats = await stats_repo.overview(db)
    return ui.admin_home(stats), admin_kb(settings.maintenance)


async def users_screen(db, page: int, query: str = ''):
    _, total = await users_repo.search(db, query, 1, 0)
    pages = page_count(total, PAGE_SIZE)
    page = max(1, min(page, pages))
    rows, total = await users_repo.search(db, query, PAGE_SIZE, (page - 1) * PAGE_SIZE)
    entries = [
        (row.id, f"{row.display_name} {S.DOT} @{row.username or 'no username'} {S.DOT} {row.id}")
        for row in rows
    ]
    return ui.users_page(rows, total, page, pages), users_list_kb(page, pages, entries)


async def user_card_screen(db, user_id: int):
    row = await users_repo.get(db, user_id)
    if row is None:
        return None, None
    stats = await users_repo.user_stats(db, user_id)
    return ui.user_card(row, stats['favorites'], stats['saved_images'], stats['history']), user_card_kb(row.id, row.is_active)


def _user_id(arg) -> int | None:
    try:
        return int(str(arg).strip())
    except (TypeError, ValueError):
        return None


async def csv_payload(db) -> bytes:
    rows, _ = await users_repo.search(db, '', 100000, 0)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        'id', 'username', 'first_name', 'last_name', 'language_code', 'created_at',
        'last_seen_at', 'interactions', 'saved_posts', 'saved_images', 'is_active', 'bot_blocked',
    ])
    for row in rows:
        stats = await users_repo.user_stats(db, row.id)
        writer.writerow([
            row.id, row.username or '', row.first_name or '', row.last_name or '',
            row.language_code or '', row.created_at, row.last_seen_at, row.request_count or 0,
            stats['favorites'], stats['saved_images'], int(bool(row.is_active)), int(bool(row.bot_blocked)),
        ])
    return buffer.getvalue().encode('utf-8')


@router.message(Command('admin'))
async def admin_command(message: Message, db, user):
    if not await guard(message, db):
        return
    text, keyboard = await admin_screen(db)
    await message.answer(text, reply_markup=keyboard)


@router.message(Command('users'))
async def users_command(message: Message, command: CommandObject, db, user):
    if not await guard(message, db):
        return
    page = _user_id(command.args) or 1
    LAST_QUERY.pop(message.from_user.id, None)
    text, keyboard = await users_screen(db, page)
    await message.answer(text, reply_markup=keyboard)


@router.message(Command('find'))
async def find_command(message: Message, command: CommandObject, db, user, state):
    if not await guard(message, db):
        return
    query = (command.args or '').strip()
    if not query:
        await state.set_state(AdminFlow.find_user)
        return await message.answer(ui.find_prompt())
    LAST_QUERY[message.from_user.id] = query
    text, keyboard = await users_screen(db, 1, query)
    await message.answer(text, reply_markup=keyboard)


@router.message(AdminFlow.find_user)
async def find_input(message: Message, db, user, state):
    if not await guard(message, db):
        return
    await state.clear()
    query = (message.text or '').strip()
    LAST_QUERY[message.from_user.id] = query
    text, keyboard = await users_screen(db, 1, query)
    await message.answer(text, reply_markup=keyboard)


@router.message(Command('user'))
async def user_command(message: Message, command: CommandObject, db, user):
    if not await guard(message, db):
        return
    user_id = _user_id(command.args)
    if user_id is None:
        return await message.answer('Usage: /user <telegram_id>')
    text, keyboard = await user_card_screen(db, user_id)
    if text is None:
        return await message.answer('No such user.')
    await message.answer(text, reply_markup=keyboard)


@router.message(Command('block'))
async def block_command(message: Message, command: CommandObject, db, user):
    await _set_active(message, db, command.args, False)


@router.message(Command('unblock'))
async def unblock_command(message: Message, command: CommandObject, db, user):
    await _set_active(message, db, command.args, True)


async def _set_active(message: Message, db, args, active: bool):
    if not await guard(message, db):
        return
    user_id = _user_id(args)
    if user_id is None:
        return await message.answer(f'Usage: /{"unblock" if active else "block"} <telegram_id>')
    row = await users_repo.set_active(db, user_id, active, message.from_user.id, None if active else 'admin')
    if row is None:
        return await message.answer('No such user.')
    await stats_repo.audit(db, message.from_user.id, 'unblock' if active else 'block', user_id)
    await message.answer(f"User {user_id} {'unblocked' if active else 'blocked'}.")


@router.message(Command('stats'))
async def stats_command(message: Message, db, user):
    if not await guard(message, db):
        return
    stats = await stats_repo.overview(db)
    await message.answer(ui.stats_text(stats, await stats_repo.top_saved_posts(db), await stats_repo.top_queries(db)))


@router.message(Command('export'))
async def export_command(message: Message, db, user):
    if not await guard(message, db):
        return
    await message.answer_document(BufferedInputFile(await csv_payload(db), filename='users.csv'))


@router.message(Command('audit'))
async def audit_command(message: Message, db, user):
    if not await guard(message, db):
        return
    rows = await stats_repo.recent_audit(db, 12)
    body = "\n".join(
        f"{S.BULLET} {row.created_at.strftime('%m-%d %H:%M') if row.created_at else ''} {S.DOT} {row.action} {S.DOT} {row.target or '-'}"
        for row in rows
    ) or f"{S.BULLET} No admin actions recorded yet."
    await message.answer(ui.screen('Audit log', body), reply_markup=admin_back_kb())


@router.callback_query(F.data.startswith('a:'))
async def admin_callback(call: CallbackQuery, db, user, state):
    if not await guard(call, db):
        return
    parts = call.data.split(':')
    screen = parts[1] if len(parts) > 1 else 'home'
    arg = parts[2] if len(parts) > 2 else None

    if screen == 'home':
        await call.answer()
        text, keyboard = await admin_screen(db)
        return await viewer.swap_screen(call.message, text, keyboard)

    if screen == 'find':
        await call.answer()
        await state.set_state(AdminFlow.find_user)
        return await viewer.swap_screen(call.message, ui.find_prompt(), admin_back_kb())

    if screen == 'users':
        await call.answer()
        query = LAST_QUERY.get(call.from_user.id, '')
        text, keyboard = await users_screen(db, _user_id(arg) or 1, query)
        return await viewer.swap_screen(call.message, text, keyboard)

    if screen == 'user':
        user_id = _user_id(arg)
        text, keyboard = await user_card_screen(db, user_id) if user_id else (None, None)
        await call.answer()
        if text is None:
            return await call.answer('No such user.', show_alert=True)
        return await viewer.swap_screen(call.message, text, keyboard)

    if screen in ('block', 'unblock'):
        user_id = _user_id(arg)
        if user_id is None:
            return await call.answer('Bad user id.', show_alert=True)
        active = screen == 'unblock'
        await users_repo.set_active(db, user_id, active, call.from_user.id, None if active else 'admin')
        await stats_repo.audit(db, call.from_user.id, screen, user_id)
        await call.answer(f"User {user_id} {'unblocked' if active else 'blocked'}.")
        text, keyboard = await user_card_screen(db, user_id)
        if text is None:
            return
        return await viewer.swap_screen(call.message, text, keyboard)

    if screen == 'stats':
        await call.answer()
        stats = await stats_repo.overview(db)
        text = ui.stats_text(stats, await stats_repo.top_saved_posts(db), await stats_repo.top_queries(db))
        return await viewer.swap_screen(call.message, text, admin_back_kb())

    if screen == 'export':
        await call.answer('Building the CSV...')
        return await call.message.answer_document(BufferedInputFile(await csv_payload(db), filename='users.csv'))

    if screen == 'audit':
        await call.answer()
        rows = await stats_repo.recent_audit(db, 12)
        body = "\n".join(
            f"{S.BULLET} {row.created_at.strftime('%m-%d %H:%M') if row.created_at else ''} {S.DOT} {row.action} {S.DOT} {row.target or '-'}"
            for row in rows
        ) or f"{S.BULLET} No admin actions recorded yet."
        return await viewer.swap_screen(call.message, ui.screen('Audit log', body), admin_back_kb())

    if screen == 'maintenance':
        settings.maintenance = not settings.maintenance
        await call.answer('Maintenance ' + ('on' if settings.maintenance else 'off'))
        text, keyboard = await admin_screen(db)
        return await viewer.swap_screen(call.message, text, keyboard)

    if screen in ('saved', 'history'):
        user_id = _user_id(arg)
        if user_id is None:
            return await call.answer('Bad user id.', show_alert=True)
        await call.answer()
        if screen == 'saved':
            rows, total = await content_repo.list_favorites(db, user_id, 10, 0)
            title = f"Saved posts {S.DOT} {user_id}"
            lines = [f"{S.BULLET} {ui.safe(row.post_title)[:70]}" for row in rows]
        else:
            rows, total = await content_repo.list_history(db, user_id, 10, 0)
            title = f"History {S.DOT} {user_id}"
            lines = [f"{S.BULLET} {ui.safe(row.post_title)[:70]}" for row in rows]
        body = "\n".join([ui.kv('Entries', total), ''] + (lines or [f"{S.BULLET} Nothing here."]))
        return await viewer.swap_screen(call.message, ui.screen(title, body), user_card_kb(user_id, True))

    return await call.answer()
