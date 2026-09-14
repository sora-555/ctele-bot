from aiogram import Router
from aiogram.types import Message
router=Router()
@router.message()
async def fallback(message:Message): await message.answer('Use /menu to open navigation, or /search to find a post.')
