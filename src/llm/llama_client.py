import requests
import time

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"

def generate(prompt: str) -> str:
    start = time.time()

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 256,
                "temperature": 0.1,
                "num_ctx": 14000,
                "num_thread": 4,
                "top_k": 1,
                "top_p": 0.9,
                "repeat_penalty": 1.0,
                "mirostat": 0
            }
        },
        timeout=300
    )

    print(f"  Запрос выполнялся {time.time() - start:.1f} сек")
    response.raise_for_status()
    return response.json()["response"]