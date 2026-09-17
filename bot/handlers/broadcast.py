import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.database.models import BroadcastRun
from bot.database.repository import stats as stats_repo
from bot.handlers import viewer
from bot.handlers.admin import admin_screen, guard
from bot.keyboards.inline import admin_back_kb, broadcast_control_kb, broadcast_kb
from bot.services.broadcast import SEGMENTS, engine
from bot.services.pagination import human_eta
from bot.states.user import AdminFlow
from bot.texts import symbols as S
from bot.texts import ui

log = logging.getLogger(__name__)
router = Router()


def label_for(segment: str) -> str:
    return dict(SEGMENTS).get(segment, 'All active users')


def _int(value):
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


async def preview_screen(db, payload):
    segment = payload.get('segment', 'all')
    count = await engine.count(segment)
    ready = bool(payload.get('message_id')) and count > 0
    return ui.broadcast_preview(label_for(segment), count), broadcast_kb(SEGMENTS, segment, ready)


@router.message(Command('broadcast'))
async def broadcast_command(message: Message, db, user, state):
    if not await guard(message, db):
        return
    await state.set_state(AdminFlow.broadcast_compose)
    await state.update_data(segment='all')
    await message.answer(ui.broadcast_prompt())


@router.message(AdminFlow.broadcast_compose)
async def compose(message: Message, db, user, state):
    if not await guard(message, db):
        return
    payload = await state.get_data()
    segment = payload.get('segment', 'all')
    await state.update_data(chat_id=message.chat.id, message_id=message.message_id, segment=segment)
    payload = await state.get_data()
    try:
        await message.copy_to(message.chat.id)
    except Exception:
        log.exception('could not copy the broadcast draft')
    text, keyboard = await preview_screen(db, payload)
    sent = await message.answer(text, reply_markup=keyboard)
    await state.update_data(control_chat=sent.chat.id, control_message=sent.message_id)


@router.message(Command('broadcast_status'))
async def broadcast_status(message: Message, db, user):
    if not await guard(message, db):
        return
    rows = await stats_repo.recent_broadcasts(db, 5)
    lines = [
        f"{S.BULLET} #{run.id} {S.DOT} {run.status} {S.DOT} sent {run.sent}/{run.total} {S.DOT} blocked {run.blocked} {S.DOT} failed {run.failed}"
        for run in rows
    ]
    body = "\n".join(lines) or f"{S.BULLET} No broadcasts yet."
    await message.answer(ui.screen('Broadcasts', body), reply_markup=admin_back_kb())


@router.callback_query(F.data.startswith('b:'))
async def broadcast_callback(call: CallbackQuery, db, user, state):
    if not await guard(call, db):
        return
    parts = call.data.split(':')
    action = parts[1] if len(parts) > 1 else ''
    arg = parts[2] if len(parts) > 2 else None

    if action == 'seg':
        await state.update_data(segment=arg)
        payload = await state.get_data()
        text, keyboard = await preview_screen(db, payload)
        await call.answer(f"{label_for(arg)} selected.")
        return await viewer.swap_screen(call.message, text, keyboard)

    if action == 'cancel':
        await state.clear()
        await call.answer('Cancelled.')
        text, keyboard = await admin_screen(db)
        return await viewer.swap_screen(call.message, text, keyboard)

    if action == 'send':
        payload = await state.get_data()
        chat_id, message_id = payload.get('chat_id'), payload.get('message_id')
        if not chat_id or not message_id:
            return await call.answer('Send the message you want to broadcast first.', show_alert=True)
        segment = payload.get('segment', 'all')
        total = await engine.count(segment)
        if not total:
            return await call.answer('That segment has no recipients.', show_alert=True)
        run = BroadcastRun(
            admin_id=call.from_user.id,
            chat_id=chat_id,
            message_id=message_id,
            segment=segment,
            status='running',
            total=total,
        )
        db.add(run)
        await db.flush()
        run_id = run.id
        await stats_repo.audit(db, call.from_user.id, 'broadcast', run_id, f'{segment} {total}')
        await state.clear()
        await db.commit()
        rate = max(1, settings.broadcast_rate)
        await call.answer('Broadcast started.')
        await viewer.swap_screen(
            call.message,
            ui.broadcast_progress(run, human_eta(total / rate), rate),
            broadcast_control_kb(run_id),
        )
        await engine.start(run_id, call.bot, progress=(call.message.chat.id, call.message.message_id))
        return

    if action in ('pause', 'resume', 'cancel_run'):
        run_id = _int(arg)
        if run_id is None:
            return await call.answer()
        engine.control(run_id, 'cancel' if action == 'cancel_run' else action)
        return await call.answer({'pause': 'Pausing.', 'resume': 'Resuming.', 'cancel_run': 'Cancelling.'}[action])

    return await call.answer()
