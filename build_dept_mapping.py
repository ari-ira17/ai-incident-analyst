"""
build_dept_mapping.py
─────────────────────
Создаёт JSON-маппинги для:
    - data/dept_mapping_omsk.json    (Омск г.о.)
    - data/dept_mapping_region.json  (Омская область, другое)

Запуск: python build_dept_mapping.py
"""

import json
import os
from collections import Counter, defaultdict

import pandas as pd

INPUT_FILE = "data/raw/тестовый файл.xlsx"
OUTPUT_DIR = "data"


def build_mappings(input_file: str, output_dir: str) -> None:
    print(f"Читаем данные из: {input_file}")
    df = pd.read_excel(input_file, usecols=["Муниципалитет", "Тема", "Отдел"])
    df = df.dropna(subset=["Муниципалитет", "Тема", "Отдел"])
    print(f"  Всего строк: {len(df)}")

    # 1. Маппинг для "Омск г.о." 
    omsk_df = df[df["Муниципалитет"] == "Омск г.о."]
    print(f"\n  Омск г.о.: {len(omsk_df)} строк")

    omsk_mapping: dict[str, Counter] = defaultdict(Counter)
    for _, row in omsk_df.iterrows():
        key = f"{row['Тема']}"  # только тема
        omsk_mapping[key][row["Отдел"]] += 1

    omsk_final: dict[str, str] = {}
    for key, counter in omsk_mapping.items():
        top = counter.most_common(1)[0]
        omsk_final[key] = top[0]

    os.makedirs(output_dir, exist_ok=True)
    omsk_output = os.path.join(output_dir, "dept_mapping_omsk.json")
    with open(omsk_output, "w", encoding="utf-8") as f:
        json.dump(omsk_final, f, ensure_ascii=False, indent=2)
    print(f"    Сохранено {len(omsk_final)} тем → {omsk_output}")

    # Маппинг для "Омская область, другое" 
    region_df = df[df["Муниципалитет"] == "Омская область, другое"]
    print(f"\n  Омская область, другое: {len(region_df)} строк")

    region_mapping: dict[str, Counter] = defaultdict(Counter)
    for _, row in region_df.iterrows():
        key = f"{row['Тема']}" 
        region_mapping[key][row["Отдел"]] += 1

    region_final: dict[str, str] = {}
    for key, counter in region_mapping.items():
        top = counter.most_common(1)[0]
        region_final[key] = top[0]

    region_output = os.path.join(output_dir, "dept_mapping_region.json")
    with open(region_output, "w", encoding="utf-8") as f:
        json.dump(region_final, f, ensure_ascii=False, indent=2)
    print(f"    Сохранено {len(region_final)} тем → {region_output}")

    print("\n✅ Готово!")


if __name__ == "__main__":
    build_mappings(INPUT_FILE, OUTPUT_DIR)