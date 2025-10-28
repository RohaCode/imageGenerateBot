#  Настройки бота, обязателен для работы.
TELEGRAM_BOT_TOKEN = ""

# API ключ от OpenRouter
BOT_OPENROUTER_KEY = ""

# Модели OpenRouter
MODELS = {
    "Gemini 2.5 Flash": "google/gemini-2.5-flash-image",
    "OpenAI GPT-5 Mini": "openai/gpt-5-image-mini",
    "OpenAI GPT-5": "openai/gpt-5-image",
}

# Модель по умолчанию
DEFAULT_MODEL = "Gemini 2.5 Flash"

# Основной URL для запросов
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# URL для проверки баланса
OPENROUTER_KEY_URL = "https://openrouter.ai/api/v1/key"
