import requests
import time

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"


def generate(prompt: str, options=None) -> str:
    start = time.time()
    if options is None:
        options = {
    "num_ctx": 1024,        
    "num_thread": 8,          
    "num_predict": 256,       
    "temperature": 0.1,
    "top_k": 1,              
    "mirostat": 0,            
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
        print(f"Ошибка {response.status_code}: {response.text}")  
        raise
    print(f"Запрос выполнялся {time.time() - start:.1f} сек")
    return response.json()["response"]
