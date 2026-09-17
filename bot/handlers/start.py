from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from bot.keyboards.inline import main_kb
from bot.states.user import InputFlow

router = Router()


async def edit_menu_message(message, text):
	if message.photo:
		return await message.edit_caption(caption=text, reply_markup=main_kb())
	return await message.edit_text(text, reply_markup=main_kb())


@router.message(Command('start','menu'))
async def start(message:Message): await message.answer('❖ <b>CosplayTele</b>\n━━━━━━━━━━━━━━━━━━━━\n\nBrowse cosplay galleries with one evolving screen.',reply_markup=main_kb())
@router.callback_query(F.data=='menu:main')
async def main_menu(call:CallbackQuery):
 await call.answer()
 await edit_menu_message(call.message, '❖ <b>Main menu</b>')


@router.callback_query(F.data == 'menu:search')
async def search_menu(call:CallbackQuery, state):
 await call.answer()
 await state.set_state(InputFlow.search)
 message = '❖ <b>Search</b>\n━━━━━━━━━━━━━━━━━━━━\n\nSend a name, character, or keyword.'
 await edit_menu_message(call.message, message)


@router.callback_query(F.data == 'menu:categories')
async def categories_menu(call:CallbackQuery, ctele):
 await call.answer()
 rows = await ctele.categories()
 if not rows:
  text = 'No categories are available right now.'
 else:
  lines = ['❖ <b>Categories</b>', '━━━━━━━━━━━━━━━━━━━━', '']
  lines.extend(f'• {item.name}' for item in rows[:50])
  text = '\n'.join(lines)
 await edit_menu_message(call.message, text)


@router.message(Command('help'))
async def help_(message:Message): await message.answer('Available: /start /menu /latest /search /categories /favorites /history /profile /settings /cancel')
@router.message(Command('cancel'))
async def cancel(message:Message, state):
 await state.clear()
 await message.answer('Input cancelled. Use /menu to continue.',reply_markup=main_kb())
