"""One navigable screen for search results, saved items, history and galleries.

Every list in the bot is rendered through this module, so numbered navigation,
prev/next behaviour and the gallery viewer are identical everywhere.
"""

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BufferedInputFile, CallbackQuery, InputMediaPhoto, Message

from bot.config import settings
from bot.database.repository import content as content_repo
from bot.database.models import UserSetting
from bot.keyboards.inline import album_kb, card_kb, categories_kb, gallery_kb, main_kb, saved_empty_kb
from bot.services.pagination import page_slice
from bot.services.sessions import store
from bot.states.user import InputFlow
from bot.texts import symbols as S
from bot.texts import ui

log = logging.getLogger(__name__)
router = Router()

ITEM_LIMIT = max(3, settings.items_per_page)
COLLECTIONS = ('saved_posts', 'saved_images', 'history')


def make_item(title, url=None, subtitle=None, thumbnail=None, image_url=None, image_index=None):
    return {
        'title': title,
        'url': url,
        'subtitle': subtitle,
        'thumbnail': thumbnail,
        'image_url': image_url,
        'image_index': image_index,
    }


def summary_items(page, subtitle='Source page'):
    return [
        make_item(item.title, url=item.url, thumbnail=item.thumbnail, subtitle=subtitle)
        for item in page.items
    ]


def photos_enabled() -> bool:
    return bool(settings.search_thumbnails)


async def _user_ttl(db, user_id) -> int | None:
    if not settings.auto_delete_enabled:
        return None
    return settings.auto_delete_ttl_minutes


def _empty_view(sid, data):
    mode = data.get('mode')
    if mode in ('saved_posts', 'saved_images'):
        tab = data.get('tab', 'posts')
        return ui.saved_empty(tab), saved_empty_kb(sid, tab, data.get('count_posts', 0), data.get('count_images', 0))
    if mode == 'history':
        return ui.history_empty(), main_kb()
    return ui.screen(data.get('title', 'Nothing found'), data.get('empty', 'Nothing here yet.')), None


def _not_modified(exc) -> bool:
    return 'not modified' in str(exc).lower()


# --------------------------------------------------------------------------- #
# session payload helpers
# --------------------------------------------------------------------------- #

def entry_data(mode, title, items=None, page=1, has_next=False, **extra):
    data = {
        'mode': mode,
        'title': title,
        'items': list(items or []),
        'page': page,
        'has_next': has_next,
        'index': 1,
        'tracked': False,
    }
    data.update(extra)
    return data


def reset_flow(data, **fields):
    """Keep the message identity, replace everything that describes the list."""
    keep = {
        'sid': data.get('sid'),
        'ns': data.get('ns', 's'),
        'chat_id': data.get('chat_id'),
        'message_id': data.get('message_id'),
        'media': data.get('media'),
        'tracked': data.get('tracked'),
    }
    keep.update(fields)
    keep.setdefault('items', [])
    return keep


async def arm_jump(state, sid: str, target) -> None:
    """Remember the screen so the next typed number lands on it."""
    await state.set_state(target)
    await state.update_data(sid=sid)


def _position(data, key, default=1) -> int:
    """Read a 1-based index out of a session payload defensively.

    A payload written by an older build could hold a dictionary here, which
    used to abort every callback that touched the screen.
    """
    value = data.get(key)
    return value if isinstance(value, int) and value >= 1 else default


def _tabs(data, sid):
    if data.get('mode') not in ('saved_posts', 'saved_images'):
        return None
    tab = data.get('tab', 'posts')
    posts = data.get('count_posts', 0)
    images = data.get('count_images', 0)
    return [
        (f"{S.TABS_ON if tab == 'posts' else S.TABS_OFF} Posts {S.DOT} {posts}", f"f:{sid}:tab:posts"),
        (f"{S.TABS_ON if tab == 'images' else S.TABS_OFF} Images {S.DOT} {images}", f"f:{sid}:tab:images"),
    ]


def _view(data, sid, index):
    item = data['items'][index - 1]
    mode = data.get('mode', 'search')
    total = len(data['items']) if mode in ('search', 'listing') else data.get('total', len(data['items']))
    text = ui.result_card(
        data.get('title', 'Results'),
        item,
        index,
        total,
        has_next=bool(data.get('has_next')),
        note=data.get('note'),
        ttl_minutes=data.get('ttl'),
    )
    keyboard = card_kb(
        data.get('ns', 's'),
        sid,
        index,
        total,
        mode,
        has_next=bool(data.get('has_next')),
        tabs=_tabs(data, sid),
    )
    return item, text, keyboard


async def main_menu_screen(db, user):
    """The one place the main menu text and keyboard are built."""
    posts = await content_repo.count_favorites(db, user.id)
    images = await content_repo.count_saved_images(db, user.id)
    rows, _ = await content_repo.list_history(db, user.id, 1, 0)
    last = rows[0] if rows else None
    return ui.main_menu(user, posts, images, last.post_title if last else None), main_kb(has_continue=last is not None)


async def _delete(bot, chat_id, message_id):
    if chat_id is None or message_id is None:
        return
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass


async def _apply(bot, data, text, keyboard, photo=None):
    """Edit the screen in place, adapting to whether it currently holds media."""
    chat_id, message_id = data.get('chat_id'), data.get('message_id')
    if chat_id is None or message_id is None:
        return
    has_media = bool(data.get('media'))
    if photo and has_media:
        try:
            await bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=InputMediaPhoto(media=photo, caption=text, parse_mode='HTML'),
                reply_markup=keyboard,
            )
            return
        except TelegramBadRequest as exc:
            if _not_modified(exc):
                return
    elif photo is None and has_media:
        try:
            await bot.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id,
                caption=text,
                parse_mode='HTML',
                reply_markup=keyboard,
            )
            return
        except TelegramBadRequest as exc:
            if _not_modified(exc):
                return
    elif photo is None and not has_media:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=keyboard,
            )
            return
        except TelegramBadRequest as exc:
            if _not_modified(exc):
                return
    await _replace(bot, data, text, keyboard, photo)


async def _replace(bot, data, text, keyboard, photo=None):
    """The screen cannot be converted in place, so send a new one."""
    chat_id, message_id = data.get('chat_id'), data.get('message_id')
    sent = None
    if photo:
        try:
            sent = await bot.send_photo(chat_id, photo, caption=text, parse_mode='HTML', reply_markup=keyboard)
        except Exception:
            sent = None
    if sent is None:
        photo = None
        sent = await bot.send_message(chat_id, text, reply_markup=keyboard)
    data['chat_id'], data['message_id'] = sent.chat.id, sent.message_id
    data['media'] = bool(photo)
    data['tracked'] = False
    await _delete(bot, chat_id, message_id)


async def _track(bot, db, user_id, data):
    if data.get('tracked') or data.get('mode') not in ('search', 'listing'):
        return
    ttl = await _user_ttl(db, user_id)
    if not ttl:
        return
    chat_id, message_id = data.get('chat_id'), data.get('message_id')
    if chat_id is None or message_id is None:
        return
    try:
        await content_repo.track_message(db, chat_id, message_id, user_id, ttl)
        data['tracked'] = True
        data['ttl'] = ttl
    except Exception:
        log.exception('could not track message for auto-delete')


# --------------------------------------------------------------------------- #
# list loading
# --------------------------------------------------------------------------- #

async def _fetch_page(data, ctele, page_number):
    source = data.get('source', 'search')
    if source == 'category':
        return await ctele.category(data['query'], page_number)
    if source == 'latest':
        return await ctele.latest(page_number)
    if source == 'popular':
        return await ctele.popular(max(0, page_number - 1))
    return await ctele.search(data['query'], page_number)


async def _extend(data, index, ctele):
    """Pull more source pages until the requested index is available."""
    while index > len(data.get('items') or []) and data.get('has_next') and ctele is not None:
        next_page = int(data.get('page', 1)) + 1
        page = await _fetch_page(data, ctele, next_page)
        if not page.items:
            data['has_next'] = False
            break
        data['items'] = list(data.get('items') or []) + summary_items(page, data.get('note') or 'Source page')
        data['page'] = next_page
        data['has_next'] = bool(page.has_next)
    return index


async def _load_collection(db, user_id, data, index):
    mode = data.get('mode')
    if mode == 'saved_posts':
        total = await content_repo.count_favorites(db, user_id)
    elif mode == 'saved_images':
        total = await content_repo.count_saved_images(db, user_id)
    else:
        total = await content_repo.count_history(db, user_id)
    data['total'] = total
    if not total:
        data['items'] = []
        return index
    index = max(1, min(index, total))
    page, offset = page_slice(index, ITEM_LIMIT)
    if data.get('page') == page and data.get('items'):
        return index
    if mode == 'saved_posts':
        rows, _ = await content_repo.list_favorites(db, user_id, ITEM_LIMIT, offset)
        items = [make_item(row.post_title, url=row.post_url, subtitle='Saved post', thumbnail=row.thumbnail) for row in rows]
    elif mode == 'saved_images':
        rows, _ = await content_repo.list_saved_images(db, user_id, ITEM_LIMIT, offset)
        items = [
            make_item(
                row.post_title,
                url=row.post_url,
                subtitle=f'Saved image {S.DOT} #{row.image_index}',
                thumbnail=row.image_url,
                image_url=row.image_url,
                image_index=row.image_index,
            )
            for row in rows
        ]
    else:
        rows, _ = await content_repo.list_history(db, user_id, ITEM_LIMIT, offset)
        items = [make_item(row.post_title, url=row.post_url, subtitle='Viewed') for row in rows]
    data['items'] = items
    data['page'] = page
    return index


async def _prepare(db, user_id, data, index, ctele):
    if data.get('mode') in ('search', 'listing'):
        index = await _extend(data, index, ctele)
    elif data.get('mode') in COLLECTIONS:
        index = await _load_collection(db, user_id, data, index)
        data['count_posts'] = await content_repo.count_favorites(db, user_id)
        data['count_images'] = await content_repo.count_saved_images(db, user_id)
    items = data.get('items') or []
    if items:
        index = max(1, min(index, len(items)))
    data['index'] = index
    return index


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #

async def start_card(message, ns, data, index=1, ctele=None, db=None, user_id=None):
    """Send the first message of a flow and open a session for it."""
    user_id = user_id or message.from_user.id
    sid = await store.create(db, user_id, data)
    data['sid'] = sid
    data['ns'] = ns
    data['chat_id'] = message.chat.id
    data['message_id'] = None
    await _prepare(db, user_id, data, index, ctele)
    if not data.get('items'):
        text, keyboard = _empty_view(sid, data)
        sent = await message.answer(text, reply_markup=keyboard)
        data['chat_id'], data['message_id'], data['media'] = sent.chat.id, sent.message_id, False
        await store.update(db, sid, data)
        return sid
    index = data['index']
    await _track(message.bot, db, user_id, data)
    item, text, keyboard = _view(data, sid, index)
    photo = item.get('thumbnail') if photos_enabled() else None
    sent = None
    if photo:
        try:
            sent = await message.answer_photo(photo, caption=text, parse_mode='HTML', reply_markup=keyboard)
        except Exception:
            sent = None
    if sent is None:
        photo = None
        sent = await message.answer(text, reply_markup=keyboard)
    data['chat_id'], data['message_id'], data['media'] = sent.chat.id, sent.message_id, bool(photo)
    await store.update(db, sid, data)
    await _track(message.bot, db, user_id, data)
    await store.update(db, sid, data)
    return sid


async def show_card(bot, ns, sid, data, index, db, user_id, ctele=None):
    await _prepare(db, user_id, data, index, ctele)
    if not data.get('items'):
        text, keyboard = _empty_view(sid, data)
        await _apply(bot, data, text, keyboard)
        await store.update(db, sid, data)
        return
    index = data['index']
    await _track(bot, db, user_id, data)
    item, text, keyboard = _view(data, sid, index)
    photo = item.get('thumbnail') if photos_enabled() else None
    await _apply(bot, data, text, keyboard, photo)
    await store.update(db, sid, data)


async def show_gallery(bot, sid, data, index, db, user_id):
    setting = await db.get(UserSetting, user_id)
    if setting is not None and setting.delivery_mode == 'album':
        return await show_album_gallery(bot, sid, data, (index - 1) // max(1, setting.images_per_page) + 1, db, user_id)
    post = data['post']
    total = len(post.images)
    index = max(1, min(index, total))
    data['image'] = index
    saved_indexes = await content_repo.saved_image_indexes(db, user_id, post.url)
    saved_post = await content_repo.is_favorite(db, user_id, post.url)
    await store.update(db, sid, data)
    await _track(bot, db, user_id, data)
    text = ui.gallery_caption(post, index, saved=index in saved_indexes, ttl_minutes=data.get('ttl'))
    keyboard = gallery_kb(
        sid,
        index,
        total,
        saved_image=index in saved_indexes,
        saved_post=saved_post,
    )
    await _apply(bot, data, text, keyboard, post.images[index - 1])
    await store.update(db, sid, data)


async def show_album_gallery(bot, sid, data, batch, db, user_id):
    """Render one user-sized batch as a Telegram media group."""
    post = data['post']
    setting = await db.get(UserSetting, user_id)
    per_page = setting.images_per_page if setting else settings.images_per_page
    per_page = max(1, min(10, per_page))
    batches = max(1, (len(post.images) + per_page - 1) // per_page)
    batch = max(1, min(batch, batches))
    start = (batch - 1) * per_page
    images = post.images[start:start + per_page]
    old_album = data.get('album_message_ids') or []
    await _delete(bot, data.get('chat_id'), data.get('message_id'))
    for message_id in old_album:
        await _delete(bot, data.get('chat_id'), message_id)
    if len(images) == 1:
        sent = [await bot.send_photo(data['chat_id'], images[0])]
    else:
        media = [InputMediaPhoto(media=image) for image in images]
        sent = await bot.send_media_group(data['chat_id'], media)
    data['album_batch'] = batch
    data['album_message_ids'] = [item.message_id for item in sent]
    data['media'] = False
    data['message_id'] = None
    caption = ui.gallery_caption(post, start + 1, saved=False, ttl_minutes=data.get('ttl'))
    control = await bot.send_message(data['chat_id'], caption, reply_markup=album_kb(sid, batch, batches))
    data['message_id'] = control.message_id
    await store.update(db, sid, data)


async def open_post(bot, sid, data, url, ctele, db, user_id, index=1, thumbnail=None):
    try:
        post = await ctele.post(url)
    except Exception:
        log.exception('could not load post %s', url)
        return False
    if not post.images:
        return False
    data['post'] = post
    data['return_index'] = int(data.get('index', 1))
    await content_repo.record_view(db, user_id, post.url, post.title)
    if thumbnail and isinstance(data.get('items'), list) and data['items']:
        current = data['items'][data.get('index', 1) - 1]
        if current.get('url') == post.url:
            current['thumbnail'] = current.get('thumbnail') or thumbnail
    await show_gallery(bot, sid, data, index, db, user_id)
    return True


async def show_categories(bot, sid, data, page, db, user_id):
    items = data.get('items') or []
    total = len(items)
    per_page = ITEM_LIMIT
    pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, pages))
    start = (page - 1) * per_page
    entries = [(start + offset + 1, item['title']) for offset, item in enumerate(items[start:start + per_page])]
    from bot.keyboards.inline import categories_kb

    data['page'] = page
    await store.update(db, sid, data)
    keyboard = categories_kb(sid, entries, page, pages)
    text = ui.categories_text(total)
    await _apply(bot, data, text, keyboard)
    await store.update(db, sid, data)


async def start_categories(message, ctele, db, user):
    try:
        rows = await ctele.categories()
    except Exception:
        log.exception('categories failed')
        return None
    if not rows:
        return None
    data = entry_data('categories', 'Categories', items=[make_item(row.name, url=row.path) for row in rows])
    sid = await store.create(db, user.id, data)
    data.update({'sid': sid, 'ns': 'c', 'chat_id': message.chat.id, 'message_id': None, 'tracked': False})
    pages = max(1, (len(data['items']) + ITEM_LIMIT - 1) // ITEM_LIMIT)
    entries = [(index + 1, item['title']) for index, item in enumerate(data['items'][:ITEM_LIMIT])]
    sent = await message.answer(ui.categories_text(len(data['items'])), reply_markup=categories_kb(sid, entries, 1, pages))
    data['chat_id'], data['message_id'], data['media'] = sent.chat.id, sent.message_id, False
    await store.update(db, sid, data)
    return sid


async def swap_screen(call_message, text, keyboard):
    """Edit the message a callback came from into an unrelated screen."""
    if call_message is None:
        return
    try:
        if getattr(call_message, 'photo', None):
            return await call_message.edit_caption(caption=text, reply_markup=keyboard)
        return await call_message.edit_text(text, reply_markup=keyboard)
    except TelegramBadRequest as exc:
        if _not_modified(exc):
            return
    except Exception:
        log.exception('could not edit the screen')
    try:
        await call_message.answer(text, reply_markup=keyboard)
    except Exception:
        log.exception('could not send the screen')


async def start_gallery(message, url, ctele, db, title='Shared gallery', user_id=None):
    """Open a gallery as a brand new message (deep links, random picks)."""
    user_id = user_id or message.from_user.id
    try:
        post = await ctele.post(url)
    except Exception:
        log.exception('could not open %s', url)
        return None
    if not post.images:
        return None
    data = entry_data('search', title, items=[make_item(post.title, url=post.url, thumbnail=post.images[0])])
    data.update({'post': post, 'image': 1, 'return_index': 1})
    sid = await store.create(db, user_id, data)
    data.update({'sid': sid, 'ns': 's', 'chat_id': message.chat.id, 'message_id': None, 'tracked': False})
    await content_repo.record_view(db, user_id, post.url, post.title)
    saved_indexes = await content_repo.saved_image_indexes(db, user_id, post.url)
    saved_post = await content_repo.is_favorite(db, user_id, post.url)
    setting = await db.get(UserSetting, user_id)
    if setting is not None and setting.delivery_mode == 'album':
        await show_album_gallery(message.bot, sid, data, 1, db, user_id)
        return sid
    text = ui.gallery_caption(post, 1, saved=1 in saved_indexes, ttl_minutes=None)
    keyboard = gallery_kb(sid, 1, len(post.images), saved_image=1 in saved_indexes, saved_post=saved_post)
    try:
        sent = await message.answer_photo(post.images[0], caption=text, parse_mode='HTML', reply_markup=keyboard)
    except Exception:
        return None
    data['chat_id'], data['message_id'], data['media'] = sent.chat.id, sent.message_id, True
    await store.update(db, sid, data)
    return sid


# --------------------------------------------------------------------------- #
# callbacks
# --------------------------------------------------------------------------- #

async def handle_card(call: CallbackQuery, ns, rest, db, user, ctele, state):
    parts = rest.split(':')
    sid = parts[0]
    action = parts[1] if len(parts) > 1 else ''
    args = parts[2:]
    data = await store.get(db, sid, call.from_user.id)
    if not data:
        return await call.answer('This screen expired. Start again from /menu.', show_alert=True)
    user_id = call.from_user.id
    mode = data.get('mode', 'search')
    index = _position(data, 'index')

    if action == 'at':
        try:
            index = int(args[0])
        except (IndexError, ValueError):
            return await call.answer()
    elif action == 'prev':
        index -= 1
    elif action == 'next':
        index += 1
    elif action == 'jump':
        total = data.get('total') or len(data.get('items') or [1])
        await arm_jump(state, sid, InputFlow.jump_result)
        await call.answer()
        return await _apply(
            call.bot,
            data,
            ui.jump_prompt('Current position', index, max(index, total)),
            card_kb(ns, sid, index, max(index, total), mode, has_next=bool(data.get('has_next')), tabs=_tabs(data, sid)),
        )
    elif action == 'tab':
        tab = args[0] if args else 'posts'
        data = reset_flow(
            data,
            mode='saved_images' if tab == 'images' else 'saved_posts',
            tab='images' if tab == 'images' else 'posts',
            title='Saved images' if tab == 'images' else 'Saved posts',
            page=None,
            total=data.get('count_images' if tab == 'images' else 'count_posts', 0),
        )
        await call.answer()
        return await show_card(call.bot, ns, sid, data, 1, db, user_id)
    elif action == 'open':
        data['index'] = index
        items = data.get('items') or []
        if not items:
            return await call.answer('Nothing to open.', show_alert=True)
        item = items[max(0, min(index, len(items)) - 1)]
        await call.answer()
        opened = await open_post(
            call.bot,
            sid,
            data,
            item['url'],
            ctele,
            db,
            user_id,
            index=item.get('image_index') or 1,
            thumbnail=item.get('thumbnail'),
        )
        if not opened:
            await call.answer('That post has no viewable images.', show_alert=True)
        return
    elif action == 'back':
        await call.answer()
        text, keyboard = await main_menu_screen(db, user)
        return await swap_screen(call.message, text, keyboard)
    elif action == 'remove':
        items = data.get('items') or []
        if not items:
            return await call.answer()
        item = items[max(0, min(index, len(items)) - 1)]
        if mode == 'saved_posts':
            removed = await content_repo.remove_favorite(db, user_id, item['url'])
        elif mode == 'saved_images':
            removed = await content_repo.remove_saved_image(db, user_id, item.get('image_url') or '')
        else:
            removed = await content_repo.remove_history(db, user_id, item['url'])
        data['items'] = []
        data['page'] = None
        await call.answer('Removed.' if removed else 'Already gone.')
        return await show_card(call.bot, ns, sid, data, index, db, user_id)

    await call.answer()
    async with store.lock(sid):
        await show_card(call.bot, ns, sid, data, index, db, user_id, ctele)


async def handle_gallery(call: CallbackQuery, rest, db, user, ctele, state):
    parts = rest.split(':')
    sid = parts[0]
    action = parts[1] if len(parts) > 1 else ''
    args = parts[2:]
    data = await store.get(db, sid, call.from_user.id)
    if not data or 'post' not in data:
        return await call.answer('This gallery expired.', show_alert=True)
    user_id = call.from_user.id
    post = data['post']
    total = len(post.images)
    index = _position(data, 'image')

    if action in ('albumprev', 'albumnext', 'albumat'):
        batch = int(data.get('album_batch', 1))
        if action == 'albumprev':
            batch -= 1
        elif action == 'albumnext':
            batch += 1
        elif args:
            try:
                batch = int(args[0])
            except ValueError:
                return await call.answer()
        await call.answer()
        async with store.lock(sid):
            return await show_album_gallery(call.bot, sid, data, batch, db, user_id)

    if action == 'back':
        await call.answer()
        return await show_card(call.bot, data.get('ns', 's'), sid, data, int(data.get('return_index', 1)), db, user_id, ctele)
    if action == 'at':
        try:
            index = int(args[0])
        except (IndexError, ValueError):
            return await call.answer()
    elif action == 'prev':
        index -= 1
    elif action == 'next':
        index += 1
    elif action == 'first':
        index = 1
    elif action == 'last':
        index = total
    elif action == 'minus5':
        index -= 5
    elif action == 'plus5':
        index += 5
    elif action == 'jump':
        await arm_jump(state, sid, InputFlow.jump_image)
        await call.answer()
        return await _apply(
            call.bot,
            data,
            ui.jump_prompt('Current image', index, total),
            gallery_kb(sid, index, total),
        )
    elif action == 'info':
        saved_count = len(await content_repo.saved_image_indexes(db, user_id, post.url))
        await call.answer()
        return await _apply(call.bot, data, ui.info_text(post, index, saved_count), gallery_kb(sid, index, total))
    elif action == 'saveimg':
        image_url = post.images[max(0, min(index, total)) - 1]
        saved = await content_repo.toggle_saved_image(db, user_id, post.url, post.title, image_url, index)
        await call.answer('Image saved.' if saved else 'Image removed from saved.')
        return await show_gallery(call.bot, sid, data, index, db, user_id)
    elif action == 'savepost':
        saved = await content_repo.toggle_favorite(
            db,
            user_id,
            post.url,
            post.title,
            post.images[0] if post.images else None,
        )
        await call.answer('Post saved.' if saved else 'Post removed from saved.')
        return await show_gallery(call.bot, sid, data, index, db, user_id)
    elif action == 'download':
        await call.answer('Fetching the image...')
        image_url = post.images[max(0, min(index, total)) - 1]
        try:
            payload = await ctele.client.download_image(image_url)
        except Exception:
            log.exception('download failed')
            return await call.message.answer('Could not download that image.')
        name = image_url.rstrip('/').split('/')[-1] or 'image.jpg'
        return await call.message.answer_document(BufferedInputFile(payload, filename=name))
    elif action == 'share':
        await call.answer('Link ready.')
        username = settings.bot_username.lstrip('@')
        if not username:
            username = (await call.bot.get_me()).username
        slug = post.url.rstrip('/').split('/')[-1]
        link = f"https://t.me/{username}?start=post-{slug}"
        body = "\n".join([ui.kv('Link', f'<code>{ui.safe(link)}</code>'), '', ui.bullet('Anyone who opens it lands in this gallery.')])
        return await call.message.answer(ui.screen('Share this gallery', body))
    elif action == 'sendfriends':
        from bot.handlers.friends import open_send_menu

        await call.answer()
        return await open_send_menu(call.message, db, user, post)

    await call.answer()
    async with store.lock(sid):
        await show_gallery(call.bot, sid, data, index, db, user_id)


async def handle_categories(call: CallbackQuery, rest, db, user, ctele, state):
    parts = rest.split(':')
    sid = parts[0]
    action = parts[1] if len(parts) > 1 else ''
    args = parts[2:]
    data = await store.get(db, sid, call.from_user.id)
    if not data:
        return await call.answer('This screen expired.', show_alert=True)
    user_id = call.from_user.id
    if action == 'page':
        try:
            page = int(args[0])
        except (IndexError, ValueError):
            return await call.answer()
        await call.answer()
        return await show_categories(call.bot, sid, data, page, db, user_id)
    if action == 'at':
        items = data.get('items') or []
        try:
            item = items[int(args[0]) - 1]
        except (IndexError, ValueError):
            return await call.answer('That category is gone.', show_alert=True)
        await call.answer()
        try:
            page = await ctele.category(item['url'], 1)
        except Exception:
            log.exception('category load failed')
            return await call.answer('Could not load that category.', show_alert=True)
        fresh = reset_flow(
            data,
            mode='listing',
            query=item['url'],
            title=f"Category {S.DOT} {item['title']}",
            items=summary_items(page, item['title']),
            page=1,
            has_next=bool(page.has_next),
            index=1,
        )
        return await show_card(call.bot, fresh.get('ns', 's'), sid, fresh, 1, db, user_id, ctele)
    return await call.answer()


@router.callback_query(F.data.startswith('s:'))
async def card_callback(call: CallbackQuery, db, user, ctele, state):
    await handle_card(call, 's', call.data[2:], db, user, ctele, state)


@router.callback_query(F.data.startswith('f:'))
async def collection_callback(call: CallbackQuery, db, user, ctele, state):
    await handle_card(call, 'f', call.data[2:], db, user, ctele, state)


@router.callback_query(F.data.startswith('c:'))
async def categories_callback(call: CallbackQuery, db, user, ctele, state):
    await handle_categories(call, call.data[2:], db, user, ctele, state)


@router.callback_query(F.data.startswith('g:'))
async def gallery_callback(call: CallbackQuery, db, user, ctele, state):
    await handle_gallery(call, call.data[2:], db, user, ctele, state)


@router.message(InputFlow.jump_result)
async def jump_result_input(message: Message, db, user, ctele, state):
    payload = await state.get_data()
    sid = payload.get('sid')
    data = await store.get(db, sid, message.from_user.id) if sid else None
    if not data:
        await state.clear()
        return await message.answer('That screen expired. Use /menu to continue.')
    try:
        index = int((message.text or '').strip())
        assert index >= 1
    except (TypeError, ValueError, AssertionError):
        return await message.answer('Send a position number, or /cancel.')
    await state.clear()
    async with store.lock(sid):
        await show_card(message.bot, data.get('ns', 's'), sid, data, index, db, user.id, ctele)
    await _delete(message.bot, message.chat.id, message.message_id)


@router.message(InputFlow.jump_image)
async def jump_image_input(message: Message, db, user, ctele, state):
    payload = await state.get_data()
    sid = payload.get('sid')
    data = await store.get(db, sid, message.from_user.id) if sid else None
    if not data or 'post' not in data:
        await state.clear()
        return await message.answer('That gallery expired. Use /menu to continue.')
    try:
        index = int((message.text or '').strip())
        assert 1 <= index <= len(data['post'].images)
    except (TypeError, ValueError, AssertionError):
        return await message.answer('Send an image number from the current gallery, or /cancel.')
    await state.clear()
    async with store.lock(sid):
        await show_gallery(message.bot, sid, data, index, db, user.id)
    await _delete(message.bot, message.chat.id, message.message_id)
