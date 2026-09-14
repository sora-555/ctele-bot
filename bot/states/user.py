"""FSM states for user-facing flows."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class SearchQuery(StatesGroup):
    query = State()


class SearchJump(StatesGroup):
    """Waiting for the result number the user types in chat."""

    number = State()
