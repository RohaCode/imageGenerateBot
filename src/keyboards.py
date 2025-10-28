from aiogram.types import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from .config import MODELS


def models_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    # Кнопки моделей
    for label in MODELS:
        builder.button(text=label)
    # Кнопка API ключа
    builder.button(text="🔑 API Ключ")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def edit_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # Кнопка редактирования
    builder.button(text="✏️ Редактировать", callback_data="edit_image")
    # Возвращаем клавиатуру
    return builder.as_markup()
