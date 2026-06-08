import requests
import time

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"

def generate(prompt: str) -> str:
# Оставляем твою модель
MODEL_NAME = "qwen2.5:7b"

# Добавляем параметр options
def generate(prompt: str, options=None) -> str:
    start = time.time()
    if options is None:
        options = {
    "num_ctx": 1024,          # ← САМЫЙ ВАЖНЫЙ РЫЧАГ
    "num_thread": 8,          # или 10 (по числу ядер M4: 8 perf или 4+4/6+4)
    "num_predict": 256,       # ограничиваем длину ответа
    "temperature": 0.1,
    "top_k": 1,               # жадный выбор токена (ещё быстрее)
    "mirostat": 0,            # отключаем продвинутый сэмплинг
    "num_gpu": 999            # все слои на GPU (Metal)
}
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "options": options,
        "format": "json",
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=300)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"Ошибка {response.status_code}: {response.text}")   # ← покажет подробности
        raise
    print(f"Запрос выполнялся {time.time() - start:.1f} сек")
    return response.json()["response"]
