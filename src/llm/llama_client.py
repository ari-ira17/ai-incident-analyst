"""
llama_client.py
────────────────
Клиент для Ollama API с обратной совместимостью.
Поддерживает как старый вызов generate(prompt), так и новый с кастомными options.
"""

import requests
import time

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"

# Параметры по умолчанию
DEFAULT_OPTIONS = {
    "num_predict": 256,
    "temperature": 0.1,
    "num_ctx": 14000,     
    "num_thread": 4,
    "top_k": 40,
    "top_p": 0.9,
    "repeat_penalty": 1.0,
    "mirostat": 0,
}


def generate(prompt: str, options=None, use_json_format: bool = False) -> str:
    """
    Универсальная функция генерации текста через Ollama.
    
    Args:
        prompt: текст запроса
        options: словарь с параметрами модели (если None — используются DEFAULT_OPTIONS)
        use_json_format: если True, добавляет "format": "json" в payload
    
    Returns:
        строка с ответом модели
    """
    start = time.time()
    
    # Используем переданные options или стандартные
    if options is None:
        options = DEFAULT_OPTIONS.copy()
    
    # Формируем payload
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "options": options,
        "stream": False
    }
    
    # Добавляем JSON формат только если явно запрошено
    if use_json_format:
        payload["format"] = "json"
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=300)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"Ошибка {response.status_code}: {response.text}")
        raise
    
    elapsed = time.time() - start
    print(f"  Запрос выполнялся {elapsed:.1f} сек")
    
    return response.json()["response"]


# Для обратной совместимости со старым кодом (кто вызывал generate(prompt))
# Оставляем возможность переопределить параметры через глобальные переменные
def set_default_options(options: dict):
    """Позволяет изменить параметры по умолчанию глобально"""
    global DEFAULT_OPTIONS
    DEFAULT_OPTIONS.update(options)


def set_model_name(model: str):
    """Позволяет изменить модель глобально"""
    global MODEL_NAME
    MODEL_NAME = model