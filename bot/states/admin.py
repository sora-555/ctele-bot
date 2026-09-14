"""FSM states for admin flows."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class BroadcastFlow(StatesGroup):
    content = State()
    confirm = State()


class UserSearch(StatesGroup):
    query = State()


class UserNote(StatesGroup):
    text = State()


class AddAdmin(StatesGroup):
    user_id = State()
    role = State()