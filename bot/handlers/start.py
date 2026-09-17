import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.database.repository import content as content_repo
from bot.handlers import viewer
from bot.texts import ui

log = logging.getLogger(__name__)
router = Router()


async def main_menu_payload(db, user):
    return await viewer.main_menu_screen(db, user)


async def send_main_menu(message, db, user):
    text, keyboard = await main_menu_payload(db, user)
    await message.answer(text, reply_markup=keyboard)


@router.message(Command('start'))
async def start(message: Message, command: CommandObject, db, user, ctele):
    payload = (command.args or '').strip()
    if payload.startswith('post-'):
        slug = payload[5:].strip()
        url = slug if slug.startswith('http') else f"{settings.source_base_url.rstrip('/')}/{slug.lstrip('/')}"
        sid = await viewer.start_gallery(message, url, ctele, db, title='Shared gallery', user_id=message.from_user.id)
        if sid:
            return
        await message.answer(ui.notice('Not available', 'That gallery could not be opened. Try a search instead.'))
    await send_main_menu(message, db, user)


@router.message(Command('menu'))
async def menu(message: Message, db, user):
    await send_main_menu(message, db, user)


@router.message(Command('help'))
async def help_command(message: Message):
    await message.answer(ui.help_text())


@router.message(Command('about'))
async def about(message: Message):
    await message.answer(ui.about_text(settings.source_base_url))


@router.message(Command('cancel'))
async def cancel(message: Message, state, db, user):
    await state.clear()
    await message.answer('Input cancelled.', reply_markup=None)
    await send_main_menu(message, db, user)


async def edit_to_main(call: CallbackQuery, db, user):
    text, keyboard = await main_menu_payload(db, user)
    await viewer.swap_screen(call.message, text, keyboard)


@router.callback_query(F.data == 'menu:main')
async def menu_main(call: CallbackQuery, db, user, state):
    await state.clear()
    await call.answer()
    await edit_to_main(call, db, user)


@router.callback_query(F.data == 'menu:help')
async def menu_help(call: CallbackQuery):
    await call.answer()
    await viewer.swap_screen(call.message, ui.help_text(), None)


@router.callback_query(F.data == 'menu:about')
async def menu_about(call: CallbackQuery):
    await call.answer()
    await viewer.swap_screen(call.message, ui.about_text(settings.source_base_url), None)


@router.callback_query(F.data == 'menu:continue')
async def menu_continue(call: CallbackQuery, db, user, ctele):
    rows, _ = await content_repo.list_history(db, user.id, 1, 0)
    if not rows:
        return await call.answer('Nothing to continue yet.', show_alert=True)
    await call.answer()
    sid = await viewer.start_gallery(call.message, rows[0].post_url, ctele, db, title='Continue', user_id=user.id)
    if not sid:
        await call.message.answer(ui.notice('Not available', 'That gallery could not be opened.'))
