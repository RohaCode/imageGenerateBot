import asyncio
from functools import partial

from aiogram import Bot, Dispatcher
from aiogram.filters import Command

from src.config import TELEGRAM_BOT_TOKEN

from src.handlers.commands import cmd_start
from src.handlers.callbacks import cb_handler

from src.handlers.messages import handle_message


async def main():
    print("Bot started")

    # Инициализация бота и диспетчера
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()

    # Регистрация обработчиков команд
    dp.message.register(cmd_start, Command("start"))



    # Регистрация обработчика колбэков
    dp.callback_query.register(cb_handler)

    # Регистрация обработчика сообщений
    dp.message.register(partial(handle_message, bot=bot))

    await dp.start_polling(bot)
    print("Bot started in polling mode")


if __name__ == "__main__":
    asyncio.run(main())
