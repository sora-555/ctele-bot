"""Admin panel keyboards. Every callback is re-authorised by the admin filter."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.services.pagination import PageInfo
from bot.texts.symbols import IMPORTANT, NEXT, PENDING, PREV, SUCCESS
from bot.utils.text import truncate

NOOP = "a:noop"


def panel(*, source_ok: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f"{IMPORTANT} Users", callback_data="a:users:1")
    builder.button(text="Find User", callback_data="a:find")
    builder.button(text="Blocked", callback_data="a:blocked:1")
    builder.button(text="Broadcast", callback_data="a:broadcast")
    builder.button(text="Audit Log", callback_data="a:logs:1")
    builder.button(text="Health", callback_data="a:health")
    builder.button(text="Export CSV", callback_data="a:export:users")
    builder.button(text="Reload Caches", callback_data="a:reload")
    builder.adjust(2, 2, 2, 2)
    return builder.as_markup()


def pager(prefix: str, info: PageInfo, *, with_middle: bool = True) -> list[InlineKeyboardButton]:
    buttons = [
        InlineKeyboardButton(
            text=f"{PREV} Prev" if info.has_prev else PREV,
            callback_data=f"{prefix}:{info.page - 1}" if info.has_prev else NOOP,
        )
    ]
    if with_middle:
        buttons.append(InlineKeyboardButton(text=f"Page {info.label}", callback_data=NOOP))
    buttons.append(
        InlineKeyboardButton(
            text=f"Next {NEXT}" if info.has_next else NEXT,
            callback_data=f"{prefix}:{info.page + 1}" if info.has_next else NOOP,
        )
    )
    return buttons


def users_list(sid: str, info: PageInfo, entries: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for start in range(0, len(entries), 2):
        row = [
            InlineKeyboardButton(
                text=truncate(f"{user_id} {mark}", 22), callback_data=f"a:user:{user_id}"
            )
            for user_id, mark in entries[start : start + 2]
        ]
        builder.row(*row)
    builder.row(*pager("a:users", info))
    builder.row(
        InlineKeyboardButton(text="Find", callback_data="a:find"),
        InlineKeyboardButton(text="Blocked", callback_data="a:blocked:1"),
        InlineKeyboardButton(text="Menu", callback_data="cmd:menu"),
    )
    return builder.as_markup()


def find_results(entries: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for user_id, label in entries[:10]:
        builder.row(InlineKeyboardButton(text=truncate(label, 40), callback_data=f"a:user:{user_id}"))
    builder.row(InlineKeyboardButton(text="Menu", callback_data="cmd:menu"))
    return builder.as_markup()


def user_card(user_id: int, *, is_blocked: bool, notes: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_blocked:
        builder.row(InlineKeyboardButton(text=f"{PENDING} Unblock", callback_data=f"a:unblock:{user_id}"))
    else:
        builder.row(InlineKeyboardButton(text=f"{IMPORTANT} Block", callback_data=f"a:block:{user_id}"))
    builder.row(
        InlineKeyboardButton(text="Add Note", callback_data=f"a:note:{user_id}"),
        InlineKeyboardButton(text=f"Notes ({notes})", callback_data=f"a:notes:{user_id}"),
    )
    builder.row(
        InlineKeyboardButton(text="Users", callback_data="a:users:1"),
        InlineKeyboardButton(text="Menu", callback_data="cmd:menu"),
    )
    return builder.as_markup()


def block_confirm(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f"{IMPORTANT} Confirm Block", callback_data=f"a:blockok:{user_id}")
    builder.button(text="Cancel", callback_data=f"a:user:{user_id}")
    builder.adjust(2)
    return builder.as_markup()


def blocked_list(sid: str, info: PageInfo, entries: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for user_id, reason in entries[:8]:
        builder.row(
            InlineKeyboardButton(
                text=truncate(f"{user_id} {reason}", 40), callback_data=f"a:user:{user_id}"
            )
        )
    builder.row(*pager("a:blocked", info))
    builder.row(InlineKeyboardButton(text="Menu", callback_data="cmd:menu"))
    return builder.as_markup()


def broadcast_preview() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f"{IMPORTANT} Send Now", callback_data="a:bcok")
    builder.button(text="Cancel", callback_data="a:bcnope")
    builder.adjust(2)
    return builder.as_markup()


def broadcast_running(broadcast_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Cancel", callback_data=f"a:bccancel:{broadcast_id}")
    return builder.as_markup()


def logs(sid: str, info: PageInfo) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(*pager("a:logs", info))
    builder.row(
        InlineKeyboardButton(text="Filter", callback_data=f"a:logfilter:{sid}"),
        InlineKeyboardButton(text="Menu", callback_data="cmd:menu"),
    )
    return builder.as_markup()


def log_filters(actions: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for action in actions[:8]:
        builder.row(InlineKeyboardButton(text=action, callback_data=f"a:logdo:{action}"))
    builder.row(InlineKeyboardButton(text="All", callback_data="a:logdo:all"))
    return builder.as_markup()


def health(*, can_reload: bool = True) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if can_reload:
        builder.button(text="Reload Caches", callback_data="a:reload")
    builder.button(text="Menu", callback_data="cmd:menu")
    builder.adjust(2)
    return builder.as_markup()


def admins() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Add Admin", callback_data="a:addadmin")
    builder.button(text="Remove Admin", callback_data="a:deladminprompt")
    builder.button(text="Menu", callback_data="cmd:menu")
    builder.adjust(2, 1)
    return builder.as_markup()


def role_picker(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Admin", callback_data=f"a:setrole:{user_id}:admin")
    builder.button(text="Moderator", callback_data=f"a:setrole:{user_id}:moderator")
    builder.button(text="Owner", callback_data=f"a:setrole:{user_id}:owner")
    builder.adjust(3)
    return builder.as_markup()


def maintenance(enabled: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    label = "Turn Off" if enabled else "Turn On"
    builder.button(text=label, callback_data="a:maintoggle")
    builder.button(text="Menu", callback_data="cmd:menu")
    builder.adjust(2)
    return builder.as_markup()


def reload_done() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Health", callback_data="a:health")
    builder.button(text="Menu", callback_data="cmd:menu")
    builder.adjust(2)
    return builder.as_markup()


def back_to_admin() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f"{SUCCESS} Admin Panel", callback_data="a:panel")
    builder.button(text="Menu", callback_data="cmd:menu")
    builder.adjust(2)
    return builder.as_markup()