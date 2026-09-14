"""The small persistent menu."""

from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

LATEST = "Latest"
POPULAR = "Popular"
SEARCH = "Search"
HELP = "Help"

MENU_TEXTS = {LATEST, POPULAR, SEARCH, HELP}


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=LATEST), KeyboardButton(text=POPULAR)],
            [KeyboardButton(text=SEARCH), KeyboardButton(text=HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Pick a section or send a command",
    )