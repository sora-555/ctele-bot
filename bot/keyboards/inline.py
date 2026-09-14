from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def search_kb(sid, index, has_prev, has_next):
    rows = []
    nav = []
    if has_prev:
        nav.append(InlineKeyboardButton(text="‹ Previous", callback_data=f"s:{sid}:prev"))
    nav.append(InlineKeyboardButton(text="▸ Open gallery", callback_data=f"s:{sid}:open"))
    if has_next:
        nav.append(InlineKeyboardButton(text="Next ›", callback_data=f"s:{sid}:next"))
    rows.append(nav)
    rows.append(
        [
            InlineKeyboardButton(text=str(i), callback_data=f"s:{sid}:at:{i}")
            for i in range(max(1, index - 2), index + 3)
        ]
    )
    rows += [
        [
            InlineKeyboardButton(text="↗ Jump to result", callback_data=f"s:{sid}:jump"),
            InlineKeyboardButton(text="Search again", callback_data="menu:search"),
        ],
        [InlineKeyboardButton(text="Main menu", callback_data="menu:main")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def gallery_kb(sid, index, total):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="‹ Previous", callback_data=f"g:{sid}:prev"),
                InlineKeyboardButton(text=f"{index} / {total} · Jump", callback_data=f"g:{sid}:jump"),
                InlineKeyboardButton(text="Next ›", callback_data=f"g:{sid}:next"),
            ],
            [
                InlineKeyboardButton(text="First", callback_data=f"g:{sid}:first"),
                InlineKeyboardButton(text="−5", callback_data=f"g:{sid}:minus5"),
                InlineKeyboardButton(text="+5", callback_data=f"g:{sid}:plus5"),
                InlineKeyboardButton(text="Last", callback_data=f"g:{sid}:last"),
            ],
            [
                InlineKeyboardButton(text="☆ Save", callback_data=f"g:{sid}:save"),
                InlineKeyboardButton(text="Information", callback_data=f"g:{sid}:info"),
            ],
            [InlineKeyboardButton(text="‹ Search results", callback_data=f"s:{sid}:back")],
        ]
    )


def main_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Search", callback_data="menu:search"),
                InlineKeyboardButton(text="Latest", callback_data="menu:latest"),
            ],
            [InlineKeyboardButton(text="Categories", callback_data="menu:categories")],
        ]
    )