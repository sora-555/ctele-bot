from aiogram.types import InputMediaPhoto
async def edit_photo(message,url,caption,keyboard):
 await message.edit_media(InputMediaPhoto(media=url,caption=caption,parse_mode='HTML'),reply_markup=keyboard)
