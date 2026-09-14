from aiogram.types import ReplyKeyboardMarkup,KeyboardButton
def main_reply(): return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Search'),KeyboardButton(text='Latest')]],resize_keyboard=True)
