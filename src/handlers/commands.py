from aiogram import types
from ..keyboards import models_kb


async def cmd_start(msg: types.Message):
    # Обработка команды старт
    await msg.answer(
        "Привет! Отправь текст или картинку для генерации.\n\n"
        "С помощью клавиатуры ниже можно выбрать модель или проверить баланс API ключа.",
        reply_markup=models_kb(),
    )
