from aiogram.types import BotCommand
COMMANDS=[('start','Start the bot'),('menu','Main menu'),('help','Command list'),('latest','Newest posts'),('search','Search posts'),('categories','Browse categories'),('favorites','Saved posts'),('history','Recently viewed'),('profile','Your profile'),('settings','Preferences'),('about','Bot information'),('cancel','Cancel current input')]
async def register_commands(bot): await bot.set_my_commands([BotCommand(command=c,description=d) for c,d in COMMANDS])
