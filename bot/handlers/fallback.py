from aiogram import Router
from aiogram.types import Message

from bot.keyboards.inline import main_kb
from bot.texts import ui

router = Router()


@router.message()
async def fallback(message: Message):
    await message.answer(
        ui.notice('Not sure what to do', 'Use /menu to browse, or /search to find something.'),
        reply_markup=main_kb(),
    )
