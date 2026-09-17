import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from bot.database.repository import stats as stats_repo
from bot.handlers import viewer
from bot.states.user import InputFlow
from bot.texts import symbols as S
from bot.texts import ui

log = logging.getLogger(__name__)
router = Router()

SOURCE_ERROR = ui.notice('Search unavailable', 'The source did not respond. Try again in a moment.')


async def run_search(message: Message, query: str, ctele, db, user):
    try:
        page = await ctele.search(query, 1)
    except Exception:
        log.exception('search failed for %s', query)
        return await message.answer(SOURCE_ERROR)
    if not page.items:
        return await message.answer(ui.notice('No results', f'Nothing matched {ui.safe(query)}. Try another keyword.'))
    await stats_repo.log_search(db, user.id, query)
    data = viewer.entry_data(
        'search',
        f'Search {S.DOT} {query}',
        items=viewer.summary_items(page, 'Search result'),
        page=1,
        has_next=page.has_next,
        query=query,
        source='search',
    )
    await viewer.start_card(message, 's', data, 1, ctele=ctele, db=db)


async def run_listing(message: Message, title: str, page, source: str, ctele, db, query=None):
    data = viewer.entry_data(
        'listing',
        title,
        items=viewer.summary_items(page, title),
        page=1,
        has_next=page.has_next,
        source=source,
        query=query,
    )
    await viewer.start_card(message, 's', data, 1, ctele=ctele, db=db)


async def open_source(message: Message, kind: str, ctele, db, user):
    try:
        if kind == 'latest':
            page = await ctele.latest(1)
        else:
            page = await ctele.popular(0)
    except Exception:
        log.exception('%s failed', kind)
        return await message.answer(SOURCE_ERROR)
    if not page.items:
        return await message.answer(ui.notice('Nothing to show', 'The source returned no posts right now.'))
    title = 'Latest' if kind == 'latest' else 'Popular'
    await run_listing(message, title, page, kind, ctele, db)


async def open_random(message: Message, ctele, db, user):
    try:
        item = await ctele.random_post()
    except Exception:
        log.exception('random failed')
        return await message.answer(SOURCE_ERROR)
    if item is None:
        return await message.answer(ui.notice('Nothing to show', 'The source returned no posts right now.'))
    sid = await viewer.start_gallery(message, item.url, ctele, db, title='Random pick')
    if not sid:
        await message.answer(ui.notice('Not available', 'That post has no viewable images.'))


@router.message(Command('search'))
async def search_command(message: Message, command: CommandObject, ctele, db, user, state):
    query = (command.args or '').strip()
    if not query:
        await state.set_state(InputFlow.search)
        return await message.answer(ui.search_prompt())
    await run_search(message, query, ctele, db, user)


@router.message(InputFlow.search)
async def search_input(message: Message, ctele, db, user, state):
    await state.clear()
    await run_search(message, (message.text or '').strip(), ctele, db, user)


@router.message(Command('latest'))
async def latest_command(message: Message, ctele, db, user):
    await open_source(message, 'latest', ctele, db, user)


@router.message(Command('popular'))
async def popular_command(message: Message, ctele, db, user):
    await open_source(message, 'popular', ctele, db, user)


@router.message(Command('random'))
async def random_command(message: Message, ctele, db, user):
    await open_random(message, ctele, db, user)


@router.message(Command('categories'))
async def categories_command(message: Message, ctele, db, user):
    sid = await viewer.start_categories(message, ctele, db, user)
    if not sid:
        await message.answer(ui.notice('Categories', 'No categories are available right now.'))


@router.callback_query(F.data == 'menu:search')
async def menu_search(call: CallbackQuery, state):
    await call.answer()
    await state.set_state(InputFlow.search)
    await viewer.swap_screen(call.message, ui.search_prompt(), None)


@router.callback_query(F.data == 'menu:latest')
async def menu_latest(call: CallbackQuery, ctele, db, user):
    await call.answer()
    await open_source(call.message, 'latest', ctele, db, user)


@router.callback_query(F.data == 'menu:popular')
async def menu_popular(call: CallbackQuery, ctele, db, user):
    await call.answer()
    await open_source(call.message, 'popular', ctele, db, user)


@router.callback_query(F.data == 'menu:random')
async def menu_random(call: CallbackQuery, ctele, db, user):
    await call.answer()
    await open_random(call.message, ctele, db, user)


@router.callback_query(F.data == 'menu:categories')
async def menu_categories(call: CallbackQuery, ctele, db, user):
    await call.answer()
    sid = await viewer.start_categories(call.message, ctele, db, user)
    if not sid:
        await call.message.answer(ui.notice('Categories', 'No categories are available right now.'))
