import asyncio
import base64
import requests
from aiogram import types, Bot
from ..config import TELEGRAM_BOT_TOKEN, MODELS, DEFAULT_MODEL, BOT_OPENROUTER_KEY
from ..openrouter import openrouter_generate, get_balance_sync, PaymentRequiredError
from ..keyboards import models_kb, edit_kb

# Словарь для хранения сессии
sessions: dict[int, dict] = {}


async def handle_message(msg: types.Message, bot: Bot):
    """Основной обработчик всех входящих сообщений пользователя."""

    user_id = msg.from_user.id
    # Инициализируем сессию пользователя или получаем существующую
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
    text = (msg.text or "").strip()

    is_editing_flow = False

    # Обработка состояняи кнопок

    # Проверка ожидания промта
    if sess.get("awaiting_edit_prompt"):
        sess["awaiting_edit_prompt"] = False
        if not text:
            await msg.reply(
                "Промпт для редактирования пустой. Пожалуйста, отправьте текст.",
                reply_markup=models_kb(),
            )
            return

        # Проверка сгенерированого изображения
        if sess.get("last_generated_image_b64"):
            sess["prompt"] = text
            is_editing_flow = True
        else:
            await msg.reply(
                "Нет изображения для редактирования. Начните с новой генерации.",
                reply_markup=models_kb(),
            )
            return

    # Выбор моделей
    elif text in MODELS:
        model_full = MODELS[text]
        sess["selected_model"] = model_full
        await msg.answer(
            f"✅ Модель выбрана: <b>{text}</b>",
            parse_mode="HTML",
            reply_markup=models_kb(),
        )
        return

    # Кнопка проверки баланса
    elif text == "🔑 API Ключ":
        loop = asyncio.get_event_loop()
        balance = await loop.run_in_executor(None, get_balance_sync, BOT_OPENROUTER_KEY)
        balance_text = (
            f"Баланс: {balance}" if balance else "Не удалось получить баланс."
        )
        await msg.reply(balance_text, reply_markup=models_kb())
        return

    # Обраотка входных данных

    # Проверка данных
    elif msg.photo or (
        msg.document
        and msg.document.mime_type
        and msg.document.mime_type.startswith("image/")
    ):
        file_to_download = None
        caption_text = None

        # Определение файла
        if msg.photo:
            file_to_download = msg.photo[-1]
            caption_text = msg.caption
        elif msg.document and msg.document.mime_type.startswith("image/"):
            file_to_download = msg.document
            caption_text = msg.caption

        if not file_to_download:
            await msg.reply(
                "Не удалось найти файл изображения.", reply_markup=models_kb()
            )
            return

        # Скачиваем изображение
        file = await bot.get_file(file_to_download.file_id)
        file_url = (
            f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file.file_path}"
        )
        try:
            img_bytes = requests.get(file_url, timeout=30).content
        except Exception:
            await msg.reply(
                "Не удалось скачать изображение. Попробуй ещё раз.",
                reply_markup=models_kb(),
            )
            return

        # Кодируем в base64
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        sess["images"].append(b64)
        await msg.reply(
            f"📸 Картинка сохранена (всего: {len(sess['images'])}). Отправь ещё одну или пришли промпт.",
            reply_markup=models_kb(),
        )

        # Если есть текст , используем как промт
        if caption_text:
            sess["prompt"] = caption_text.strip()
        else:
            # Если нету, то ждем
            return

    # Сообщение без картинки , используем промтом
    elif text:
        sess["prompt"] = text

    # Окончание проверок
    if not sess.get("prompt"):
        # Игнорируем данные
        if msg.content_type not in ["text", "photo", "document"]:
            return
        await msg.reply("✍️ Пришли текст-промпт.", reply_markup=models_kb())
        return

    # Генерация изображения

    # Проверка ключа
    if not BOT_OPENROUTER_KEY:
        await msg.reply(
            "⚠️ Ключ бота не задан в файле config.py.", reply_markup=models_kb()
        )
        return

    # Выбираем модель
    model_name = sess.get("selected_model") or MODELS.get(DEFAULT_MODEL)
    # Отображение имени модели
    model_label = next(
        (label for label, id in MODELS.items() if id == model_name), model_name
    )

    await msg.reply(f"🎨 Отправляю в модель '{model_label}', подожди...")

    # Список изображений
    images_to_send = []
    if is_editing_flow:
        images_to_send = [sess["last_generated_image_b64"]]
    else:
        images_to_send = sess["images"]

    # Запускаем генерации в отдельном потоке
    gen_func = openrouter_generate
    try:
        result_value = await asyncio.get_event_loop().run_in_executor(
            None,
            gen_func,
            sess["prompt"],
            images_to_send,
            model_name,
            BOT_OPENROUTER_KEY,
        )
    except PaymentRequiredError as e:
        # Недостаточно средств
        await msg.reply(
            f"⚠️ Недостаточно средств на вашем балансе OpenRouter. Пожалуйста, пополните счет.\n\nПодробности: {e}",
            reply_markup=models_kb(),
        )
        return
    except Exception:  # Ошибка соединения
        await msg.reply(
            "Произошла ошибка при вызове генерации. Попробуйте еще раз",
            reply_markup=models_kb(),
        )
        return

    # Новая сессия для генерации
    sess["images"] = []
    sess["prompt"] = None
    sess["awaiting_edit_prompt"] = False

    # Обработка ошибок от OpenRouter
    if isinstance(result_value, str):
        error_message = f"❌ Не удалось получить результат от модели: {result_value}"

        if result_value.startswith("MODEL_ERROR:"):
            error_message = f"❌ Ошибка модели: {result_value[12:]}"
        elif result_value.startswith("MODEL_REFUSED:"):
            error_message = f"❌ Модель отказалась генерировать: {result_value[15:]}"
        elif result_value.startswith("MODEL_FINISH_REASON:"):
            error_message = f"❌ Генерация завершена с причиной: {result_value[20:]}"
        elif result_value == "NO_IMAGE_RETURNED":
            error_message = "❌ Модель не вернула изображение. Возможно, промпт слишком сложный или нарушает правила."
        elif result_value == "UNKNOWN_IMAGE_FORMAT":
            error_message = "❌ Неизвестный формат изображения в ответе от модели."
        elif result_value == "JSON_PARSE_ERROR":
            error_message = (
                "❌ Ошибка при чтении ответа от OpenRouter (неверный формат JSON)."
            )

        await msg.reply(error_message, reply_markup=models_kb())
        return

    # Непредвиденная ошибка
    if not isinstance(result_value, bytes) or not result_value:
        await msg.reply(
            "❌ Неизвестная ошибка при получении результата. Попробуйте еще раз.",
            reply_markup=models_kb(),
        )
        return

    # Сохраняем последнее сгенерированное
    sess["last_generated_image_b64"] = base64.b64encode(result_value).decode("utf-8")

    # Финальный результат
    await msg.reply_photo(
        types.BufferedInputFile(result_value, filename="result.png"),
        caption="✨ Готово!",
        reply_markup=edit_kb(),
    )
