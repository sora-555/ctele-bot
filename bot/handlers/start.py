from aiogram import Router,F
from aiogram.filters import Command
from aiogram.types import Message,CallbackQuery
from bot.keyboards.inline import main_kb
router=Router()
@router.message(Command('start','menu'))
async def start(message:Message): await message.answer('❖ <b>CosplayTele</b>\n━━━━━━━━━━━━━━━━━━━━\n\nBrowse cosplay galleries with one evolving screen.',reply_markup=main_kb())
@router.callback_query(F.data=='menu:main')
async def main_menu(call:CallbackQuery): await call.answer(); await call.message.edit_text('❖ <b>Main menu</b>',reply_markup=main_kb())
@router.message(Command('help'))
async def help_(message:Message): await message.answer('Available: /start /menu /latest /search /categories /favorites /history /profile /settings /cancel')
@router.message(Command('cancel'))
async def cancel(message:Message, state):
 await state.clear()
 await message.answer('Input cancelled. Use /menu to continue.',reply_markup=main_kb())
