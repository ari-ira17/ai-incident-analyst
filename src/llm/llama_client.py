import requests
import time


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b-instruct-q4_K_M"

def generate(prompt: str) -> str:

    start = time.time()

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False
        },
        timeout=300
    )

    print(
        f"Запрос выполнялся {time.time() - start:.1f} сек"
    )

    response.raise_for_status()

    return response.json()["response"]