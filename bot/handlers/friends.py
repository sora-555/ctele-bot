import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.database.repository import friends as friends_repo
from bot.keyboards.inline import delivered_friend_message_kb, friend_management_kb, friend_request_kb, friend_send_kb, main_kb
from bot.services.sessions import store
from bot.states.user import InputFlow
from bot.texts import ui

log = logging.getLogger(__name__)
router = Router()
TOKEN_SECRET = settings.bot_token or 'friend-invite-secret'


def invite_token(user_id: int) -> str:
    digest = hmac.new(TOKEN_SECRET.encode(), str(user_id).encode(), hashlib.sha256).digest()
    return secrets.token_urlsafe(4) + digest.hex()[:32]


def public_name(user) -> str:
    username = f"@{user.username}" if user.username else "not set"
    display = ui.safe(user.display_name or "unknown")
    return f"{display} {ui.kv('Username', ui.safe(username))}"


def invite_link(token: str) -> str:
    username = settings.bot_username.lstrip('@')
    return f"https://t.me/{username}?start=friend_req_{token}"


async def show_request(message: Message, db, receiver_id: int, token: str):
    sender_id = await friends_repo.invite_owner(db, token)
    if sender_id is None:
        await message.answer(ui.notice('Friend request', 'This invite link is invalid or expired.'))
        return
    if sender_id == receiver_id:
        await message.answer(ui.notice('Friend request', 'You cannot add yourself.'))
        return
    sender = await friends_repo.resolve_user(db, sender_id)
    if sender is None:
        await message.answer(ui.notice('Friend request', 'The sender is no longer available.'))
        return
    if await friends_repo.already_friends(db, sender_id, receiver_id):
        await message.answer(ui.notice('Friend request', 'You are already friends.'))
        return
    request, created = await friends_repo.create_request(db, sender_id, receiver_id)
    if not created:
        await message.answer(ui.notice('Friend request', 'This friend request is already pending.'))
        return
    await message.answer(ui.friend_request(public_name(sender)), reply_markup=friend_request_kb(request.id))


@router.message(Command('add_friends'))
async def add_friends(message: Message, db, user):
    token = invite_token(user.id)
    expires_at = datetime.now(timezone.utc) + timedelta(days=2)
    await friends_repo.invite_for(db, user.id, token, expires_at)
    await message.answer(ui.friend_invite(invite_link(token), expires_at), reply_markup=main_kb())


async def render_friends(message, db, user):
    rows = await friends_repo.list_friends(db, user.id)
    await message.answer(ui.friends_menu(len(rows)), reply_markup=friend_management_kb(rows))


@router.message(Command('friends'))
async def friends_command(message: Message, db, user):
    await render_friends(message, db, user)


@router.callback_query(F.data == 'menu:friends')
async def menu_friends(call: CallbackQuery, db, user):
    await call.answer()
    rows = await friends_repo.list_friends(db, user.id)
    await call.message.edit_text(ui.friends_menu(len(rows)), reply_markup=friend_management_kb(rows))


@router.callback_query(F.data.startswith('friends:'))
async def friends_management(call: CallbackQuery, db, user):
    parts = call.data.split(':')
    action = parts[1] if len(parts) > 1 else ''
    friend_id = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
    if action == 'home':
        await call.answer()
        rows = await friends_repo.list_friends(db, user.id)
        return await call.message.edit_text(ui.friends_menu(len(rows)), reply_markup=friend_management_kb(rows))
    if action == 'remove':
        await friends_repo.remove_friend(db, user.id, friend_id)
        await call.answer('Friend removed.')
    elif action == 'send':
        row = await friends_repo.friendship(db, user.id, friend_id)
        if row is None:
            return await call.answer('Friend not found.', show_alert=True)
        await friends_repo.set_send_allowed(db, user.id, friend_id, not row.send_allowed)
        await call.answer('Send permission updated.')
    else:
        return await call.answer('Unknown action.', show_alert=True)
    rows = await friends_repo.list_friends(db, user.id)
    await call.message.edit_text(ui.friends_menu(len(rows)), reply_markup=friend_management_kb(rows))


async def open_send_menu(message, db, user, post):
    rows = await friends_repo.list_friends(db, user.id)
    data = {
        'mode': 'friend_send',
        'post_url': post.url,
        'post_title': post.title,
        'selected': [],
        'message': '',
        'chat_id': message.chat.id,
        'message_id': None,
    }
    sid = await store.create(db, user.id, data)
    sent = await message.answer(
        ui.friend_send_menu(rows, set(), post.title),
        reply_markup=friend_send_kb(sid, rows, set()),
    )
    data['sid'] = sid
    data['message_id'] = sent.message_id
    await store.update(db, sid, data)


async def render_send_menu(call: CallbackQuery, db, user, data):
    rows = await friends_repo.list_friends(db, user.id)
    selected = set(data.get('selected') or [])
    await call.message.edit_text(
        ui.friend_send_menu(rows, selected, data['post_title'], data.get('message', '')),
        reply_markup=friend_send_kb(data['sid'], rows, selected, data.get('message', '')),
    )


@router.callback_query(F.data.startswith('fs:'))
async def friend_send_callback(call: CallbackQuery, db, user, state):
    parts = call.data.split(':')
    sid = parts[1] if len(parts) > 1 else ''
    action = parts[2] if len(parts) > 2 else ''
    data = await store.get(db, sid, user.id)
    if not data or data.get('mode') != 'friend_send':
        return await call.answer('This send menu expired.', show_alert=True)
    if action == 'toggle':
        friend_id = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
        selected = set(data.get('selected') or [])
        if friend_id in selected:
            selected.remove(friend_id)
        else:
            selected.add(friend_id)
        data['selected'] = list(selected)
        await store.update(db, sid, data)
        await call.answer()
        return await render_send_menu(call, db, user, data)
    if action == 'message':
        await state.set_state(InputFlow.friend_message)
        await state.update_data(sid=sid)
        await call.answer()
        return await call.message.answer('Send a message of up to 1000 characters.')
    if action == 'cancel':
        await store.update(db, sid, data)
        await call.answer('Cancelled.')
        return await call.message.edit_text(ui.friend_result('cancelled'), reply_markup=main_kb())
    if action == 'send':
        selected = set(data.get('selected') or [])
        if not selected:
            return await call.answer('Select at least one friend.', show_alert=True)
        rows = await friends_repo.list_friends(db, user.id)
        sender = public_name(user)
        sent_count = 0
        for friendship, friend in rows:
            if friend.id not in selected or not await friends_repo.can_send(db, user.id, friend.id):
                continue
            try:
                await call.bot.send_message(
                    friend.id,
                    ui.friend_delivery(data['post_title'], sender, data.get('message', '')),
                    reply_markup=delivered_friend_message_kb(data['post_url'], user.id),
                )
                sent_count += 1
            except Exception:
                log.exception('could not send friend share to %s', friend.id)
        await call.answer(f'Sent to {sent_count} friend(s).')
        return await call.message.edit_text(ui.friend_result(f'sent to {sent_count} friend(s)'), reply_markup=main_kb())
    return await call.answer('Unknown action.', show_alert=True)


@router.message(InputFlow.friend_message)
async def friend_message_input(message: Message, db, user, state):
    payload = await state.get_data()
    sid = payload.get('sid')
    data = await store.get(db, sid, user.id) if sid else None
    if not data:
        await state.clear()
        return await message.answer('That send menu expired.')
    text = message.text or ''
    if len(text) > 1000:
        return await message.answer('Your message is too long. Keep it under 1000 characters.')
    data['message'] = text
    await store.update(db, sid, data)
    await state.clear()
    rows = await friends_repo.list_friends(db, user.id)
    await message.answer(
        ui.friend_send_menu(rows, set(data.get('selected') or []), data['post_title'], text),
        reply_markup=friend_send_kb(sid, rows, set(data.get('selected') or []), text),
    )


@router.callback_query(F.data == 'fmsg:delete')
async def delete_friend_message(call: CallbackQuery):
    await call.answer('Deleted.')
    await call.message.delete()


@router.callback_query(F.data.startswith('fmsg:revoke:'))
async def revoke_friend_permission(call: CallbackQuery, db, user):
    sender_id = int(call.data.rsplit(':', 1)[-1])
    await friends_repo.set_send_allowed(db, user.id, sender_id, False)
    await call.answer('Send permission revoked.')
    await call.message.edit_reply_markup(reply_markup=None)


@router.message(Command('friend_req'))
async def friend_req(message: Message, command: CommandObject, db, user):
    token = (command.args or '').strip()
    if not token:
        return await message.answer(ui.notice('Friend request', 'That invite link is incomplete.'))
    await show_request(message, db, user.id, token)


@router.callback_query(F.data.startswith('friend:'))
async def friend_decision(call: CallbackQuery, db, user):
    parts = call.data.split(':')
    if len(parts) != 3 or parts[1] not in ('accept', 'decline'):
        return await call.answer('Invalid friend request.', show_alert=True)
    request_id = int(parts[2]) if parts[2].isdigit() else 0
    request = await friends_repo.get_request(db, request_id, user.id)
    if request is None:
        return await call.answer('This request is no longer pending.', show_alert=True)
    accepted = parts[1] == 'accept'
    await friends_repo.finish_request(db, request, accepted)
    await call.answer('Friend added.' if accepted else 'Request declined.')
    await call.message.edit_text(ui.friend_result('accepted' if accepted else 'declined'), reply_markup=main_kb())
