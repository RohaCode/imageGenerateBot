from aiogram import types
from ..config import MODELS, DEFAULT_MODEL
from ..keyboards import models_kb
from ..handlers.messages import sessions


async def cb_handler(cb: types.CallbackQuery):
    # Обработчик всех CallbackQuery
    user_id = cb.from_user.id
    sess = sessions.setdefault(
        user_id,
        {
            "images": [],
            "prompt": None,
            "selected_model": MODELS.get(DEFAULT_MODEL),
            "last_generated_image_b64": None,
            "awaiting_edit_prompt": False,
        },
    )

    # Проверка кнопки редактировать
    if cb.data == "edit_image":
        if sess.get("last_generated_image_b64"):
            sess["awaiting_edit_prompt"] = True
            await cb.message.answer(
                "Отправьте новый текст для редактирования изображения ( то что вы хотели бы изменить ).",
                reply_markup=models_kb(),
            )
        else:
            await cb.answer("Нет изображения для редактирования.", show_alert=True)
        await cb.answer()
