import base64
import requests
from typing import Optional, List, Union
import json
from .config import OPENROUTER_URL, OPENROUTER_KEY_URL


# Исключения ошибок оплаты
class PaymentRequiredError(Exception):
    pass


def openrouter_generate(
    prompt: str, images_b64: List[str], model_name: str, api_key: str
) -> Optional[Union[bytes, str]]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Формируем контент messages
    content = [{"type": "text", "text": prompt}]
    for b64_image in images_b64:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"},
            }
        )

    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 4096,
    }

    try:
        r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=180)
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        # Обработка HTTP ошибок
        if e.response.status_code == 402:
            try:
                error_data = e.response.json()
                error_message = error_data.get("error", {}).get("message", "")
                raise PaymentRequiredError(error_message)
            except json.JSONDecodeError:
                raise PaymentRequiredError(
                    "Недостаточно средств на балансе OpenRouter."
                )
        # Другие HTTP ошибки
        return None
    except requests.exceptions.RequestException:
        return None

    try:
        data = r.json()

        # Неизвестная ошибка модели.
        if data.get("error"):
            error_message = data["error"].get("message", "Неизвестная ошибка модели.")
            return f"MODEL_ERROR: {error_message}"

        response_message = data["choices"][0]["message"]

        # Отказ модели
        if response_message.get("refusal"):
            refusal_reason = response_message["refusal"]
            return f"MODEL_REFUSED: {refusal_reason}"

        if (
            response_message.get("finish_reason")
            and response_message["finish_reason"] != "stop"
        ):
            finish_reason = response_message["finish_reason"]
            return f"MODEL_FINISH_REASON: {finish_reason}"

        # Проверка ключа images
        if not response_message.get("images") or not response_message["images"]:
            if response_message.get("content"):
                pass
            return "NO_IMAGE_RETURNED"

        image_url = response_message["images"][0].get("image_url", {}).get("url")

        # Если ссылка - скачиваем
        if image_url.startswith("http"):
            rr = requests.get(image_url, timeout=60)
            rr.raise_for_status()
            return rr.content
        # Если формат base64
        elif image_url.startswith("data:image"):
            header, b64_data = image_url.split(",", 1)
            return base64.b64decode(b64_data)
        else:
            return "UNKNOWN_IMAGE_FORMAT"

    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        # Ошибка парсинга JSON
        return "JSON_PARSE_ERROR"


def get_balance_sync(api_key: str) -> Optional[str]:
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        r = requests.get(OPENROUTER_KEY_URL, headers=headers, timeout=20)
        if not r.ok:
            return None

        data = r.json().get("data", {})

        # Если ключ с балансом
        limit = data.get("limit_remaining")
        if limit is not None:
            return f"Остаток: ${float(limit):.4f}"

        # Если ключ с бесплатным лимитом
        usage = data.get("usage")
        if usage is not None:
            return f"Использовано: ${float(usage):.4f}"

        return "Не удалось распознать данные о балансе"

    except Exception:
        return None
