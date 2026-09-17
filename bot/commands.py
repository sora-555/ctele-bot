from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from bot.config import settings

USER_COMMANDS = [
    ('start', 'Start the bot'),
    ('menu', 'Main menu'),
    ('search', 'Search galleries'),
    ('latest', 'Newest posts'),
    ('popular', 'Popular posts'),
    ('random', 'Random pick'),
    ('categories', 'Browse categories'),
    ('favorites', 'Saved posts and images'),
    ('history', 'Recently viewed'),
    ('add_friends', 'Create a friend invite link'),
    ('friends', 'Manage friends and permissions'),
    ('friend_req', 'Open a friend request'),
    ('suggestions', 'Send a suggestion to the admins'),
    ('profile', 'Your profile'),
    ('settings', 'Preferences'),
    ('help', 'Command list'),
    ('about', 'Bot information'),
    ('cancel', 'Cancel current input'),
]

ADMIN_COMMANDS = [
    ('admin', 'Admin panel'),
    ('broadcast', 'Message your users'),
    ('broadcast_status', 'Recent broadcasts'),
    ('users', 'Browse users'),
    ('find', 'Search users'),
    ('user', 'Open a user card'),
    ('stats', 'Bot statistics'),
    ('export', 'Export users as CSV'),
    ('audit', 'Recent admin actions'),
    ('block', 'Block a user'),
    ('unblock', 'Unblock a user'),
]


def _commands(pairs):
    return [BotCommand(command=name, description=description) for name, description in pairs]


async def register_commands(bot):
    if not settings.set_commands_on_startup:
        return
    await bot.set_my_commands(_commands(USER_COMMANDS), scope=BotCommandScopeDefault())
    if not settings.command_scope_admins:
        return
    for admin_id in settings.admin_id_list:
        try:
            await bot.set_my_commands(
                _commands(USER_COMMANDS + ADMIN_COMMANDS),
                scope=BotCommandScopeChat(chat_id=admin_id),
            )
        except Exception:
            pass
