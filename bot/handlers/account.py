import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.database.models import UserSetting
from bot.database.repository import content as content_repo
from bot.database.repository import stats as stats_repo
from bot.database.repository import users as users_repo
from bot.handlers import viewer
from bot.keyboards.inline import main_kb, settings_kb
from bot.texts import ui

log = logging.getLogger(__name__)
router = Router()

PER_PAGE_CHOICES = (3, 5, 6, 10)
TTL_CHOICES = (None, 15, 30, 60, 0)


async def setting_for(db, user_id: int) -> UserSetting:
    setting = await db.get(UserSetting, user_id)
    if setting is None:
        setting = UserSetting(user_id=user_id)
        db.add(setting)
        await db.flush()
    return setting


def settings_payload(setting: UserSetting):
    return ui.settings_text(setting), settings_kb(setting)


async def open_saved(message, db, user, tab: str = 'posts'):
    posts = await content_repo.count_favorites(db, user.id)
    images = await content_repo.count_saved_images(db, user.id)
    if tab == 'posts' and not posts and images:
        tab = 'images'
    elif tab == 'images' and not images and posts:
        tab = 'posts'
    mode = 'saved_images' if tab == 'images' else 'saved_posts'
    title = 'Saved images' if tab == 'images' else 'Saved posts'
    data = viewer.entry_data(mode, title, tab=tab)
    data['count_posts'] = posts
    data['count_images'] = images
    return await viewer.start_card(message, 'f', data, 1, db=db, user_id=user.id)


async def open_history(message, db, user):
    rows = await stats_repo.user_search_history(db, user.id)
    return await message.answer(ui.search_history(rows), reply_markup=main_kb())


@router.message(Command('profile'))
async def profile_command(message: Message, db, user):
    stats = await users_repo.user_stats(db, user.id)
    await message.answer(
        ui.profile_text(user, stats['favorites'], stats['saved_images'], stats['history']),
        reply_markup=main_kb(),
    )


@router.message(Command('favorites'))
async def favorites_command(message: Message, db, user):
    await open_saved(message, db, user)


@router.callback_query(F.data == 'menu:saved')
async def menu_saved(call: CallbackQuery, db, user):
    await call.answer()
    await open_saved(call.message, db, user)


@router.message(Command('history'))
async def history_command(message: Message, db, user):
    await open_history(message, db, user)


@router.callback_query(F.data == 'menu:history')
async def menu_history(call: CallbackQuery, db, user):
    await call.answer()
    await open_history(call.message, db, user)


@router.message(Command('settings'))
async def settings_command(message: Message, db, user):
    setting = await setting_for(db, user.id)
    text, keyboard = settings_payload(setting)
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == 'menu:settings')
async def menu_settings(call: CallbackQuery, db, user):
    await call.answer()
    setting = await setting_for(db, user.id)
    text, keyboard = settings_payload(setting)
    await viewer.swap_screen(call.message, text, keyboard)


@router.callback_query(F.data.startswith('set:'))
async def settings_toggle(call: CallbackQuery, db, user):
    key = call.data.split(':')[1] if ':' in call.data else ''
    setting = await setting_for(db, user.id)
    if key == 'delivery':
        setting.delivery_mode = 'single' if setting.delivery_mode == 'album' else 'album'
    elif key == 'perpage':
        current = setting.images_per_page if setting.images_per_page in PER_PAGE_CHOICES else PER_PAGE_CHOICES[0]
        setting.images_per_page = PER_PAGE_CHOICES[(PER_PAGE_CHOICES.index(current) + 1) % len(PER_PAGE_CHOICES)]
    elif key == 'thumbs':
        setting.show_thumbnails = not setting.show_thumbnails
    elif key == 'numbers':
        setting.numbered_nav = not setting.numbered_nav
    else:
        return await call.answer('Unknown setting.', show_alert=True)
    await db.flush()
    await call.answer('Saved.')
    text, keyboard = settings_payload(setting)
    await viewer.swap_screen(call.message, text, keyboard)
