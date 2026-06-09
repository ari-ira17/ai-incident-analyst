"""
Генерация Modelfile для Ollama на основе fine_tuning.csv.

Скрипт:
1. Загружает fine_tuning.csv с эталонными классификациями
2. Создаёт Modelfile с кратким SYSTEM промптом
3. Создаёт кастомную модель через `ollama create`
"""

import json
import pandas as pd
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
FINE_TUNING_CSV = BASE_DIR / "data" / "raw" / "fine_tuning.csv"
MODELFILE_PATH = BASE_DIR / "src" / "llm" / "Modelfile"
BASE_MODEL = "gemma:2b"
CUSTOM_MODEL_NAME = "gemma-incident-classifier"


def load_fine_tuning_data() -> pd.DataFrame:
    """Загрузка и фильтрация данных fine_tuning."""
    df = pd.read_csv(FINE_TUNING_CSV, encoding="utf-8-sig")
    df = df.dropna(subset=["is_problem", "severity", "problem_tags"]).copy()
    df["is_problem"] = df["is_problem"].astype(int)
    df["severity"] = df["severity"].astype(int)

    print(f"Загружено {len(df)} размеченных записей")
    print(f"  is_problem: {df['is_problem'].value_counts().to_dict()}")
    print(f"  severity: {df['severity'].value_counts().sort_index().to_dict()}")

    return df


def generate_modelfile() -> str:
    """Генерирует содержимое Modelfile."""

    system_prompt = """Ты аналитик муниципальных инцидентов. Классифицируй обращения граждан.

Для каждого обращения определи:
1. is_problem (0 — нет проблемы, 1 — проблема есть)
2. severity (1-5): 1=нет проблемы, 2=локальное неудобство, 3=проблема группы жителей, 4=серьёзное нарушение, 5=критическая ситуация/угроза жизни
3. problem_tags: 2-4 кратких тега (2-6 слов), отражающих суть проблемы

Верни ТОЛЬКО JSON-массив без пояснений."""

    # Без TEMPLATE — Gemma использует свой встроенный шаблон
    modelfile_content = f"""FROM {BASE_MODEL}

SYSTEM \"\"\"{system_prompt}\"\"\"

PARAMETER temperature 0.1
PARAMETER top_p 0.9
"""

    return modelfile_content


def create_ollama_model(modelfile_path: Path):
    """Создаёт кастомную модель через ollama create."""
    print(f"\nСоздание модели {CUSTOM_MODEL_NAME} из {modelfile_path}...")
    result = subprocess.run(
        ["ollama", "create", CUSTOM_MODEL_NAME, "-f", str(modelfile_path)],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        print(f"Ошибка: {result.stderr}")
        sys.exit(1)
    print(f"Модель {CUSTOM_MODEL_NAME} успешно создана!")
    print(result.stdout)


def main():
    print("=" * 60)
    print("Генерация Modelfile для кастомной модели Ollama")
    print("=" * 60)

    # 1. Загружаем данные (для статистики)
    df = load_fine_tuning_data()

    # 2. Генерируем Modelfile
    modelfile_content = generate_modelfile()

    # 3. Сохраняем Modelfile
    MODELFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODELFILE_PATH, "w", encoding="utf-8") as f:
        f.write(modelfile_content)

    print(f"\nModelfile сохранён: {MODELFILE_PATH}")
    print(f"Размер: {len(modelfile_content)} символов")

    # 4. Создаём модель в Ollama
    create_ollama_model(MODELFILE_PATH)

    print(f"\nГотово! Модель {CUSTOM_MODEL_NAME} создана.")


if __name__ == "__main__":
    main()