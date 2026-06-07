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
                "num_predict": -1,
                "temperature": 0.1,
                "num_ctx": 4096,
                "num_thread": 8,
                "top_k": 10
            }
        },

        timeout=600
    )
    
    print(f"Запрос выполнялся {time.time() - start:.1f} сек")
    response.raise_for_status()
    result = response.json()
    print(f"Ответ от Ollama получен, поле 'response' есть: {'response' in result}")
    
    return result.get("response", "")