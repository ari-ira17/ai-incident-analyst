# ============================================
# ГЕНЕРАЦИЯ ПЕРСОНАЛИЗИРОВАННЫХ ЧЕРНОВИКОВ ОТВЕТОВ ЧЕРЕЗ LLM
# ============================================
# Задача: сгенерировать черновик ответа, который:
# - Упоминает суть проблемы из жалобы (адрес, что случилось)
# - НЕ придумывает конкретные действия служб, сроки, имена
# - Оставляет место для доработки реальным сотрудником
# ============================================

import pandas as pd
import re
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.llm.llama_client import generate, MODEL_QWEN_7B, MODEL_QWEN_3B

DATA_PATH = "data/raw/testovy_fayl.xlsx"
OUTPUT_PATH = "test_results_llm_first20.csv"

# Примеры персонализированных черновиков — упоминают проблему, но без конкретики по службам
TEMPLATE_EXAMPLES = """
Пример 1:
Жалоба: Здравствуйте, на улице Пушкина уже неделю не чистят снег, тротуары завалены, пройти невозможно.
Ответ: Здравствуйте. Ваше обращение по вопросу уборки снега на ул. Пушкина получено. Информация передана в дорожную службу для проведения работ по очистке. Приносим извинения за доставленные неудобства.

Пример 2:
Жалоба: В квартире холодно, батареи еле теплые, температура в комнате +14 градусов.
Ответ: Здравствуйте. Ваше обращение по вопросу низкой температуры в квартире зарегистрировано. Для проведения проверки системы отопления просим уточнить адрес и контактные данные. Обращение будет рассмотрено в установленном порядке.

Пример 3:
Жалоба: Добрый день, мусор не вывозят уже вторую неделю, контейнеры переполнены.
Ответ: Здравствуйте. Ваше обращение по вопросу вывоза мусора получено. Информация передана региональному оператору для корректировки графика. Принимаются меры в рамках компетенции.
"""

def clean_text(text):
    if pd.isna(text) or not isinstance(text, str):
        return ""
    text = re.sub(r'\[id\d+\|([^\]]+)\]', r'\1', text)
    text = re.sub(r'\[club\d+\|([^\]]+)\]', r'\1', text)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def remove_non_russian(text):
    """
    Удаляет китайские иероглифы и другие не-русские/не-латинские символы.
    Оставляет: русские буквы, латиницу, цифры, знаки препинания.
    """
    if not isinstance(text, str):
        return text
    # Удаляем CJK Unified Ideographs (китайские иероглифы)
    text = re.sub(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]', '', text)
    # Удаляем хирагану и катакану (японские)
    text = re.sub(r'[\u3040-\u309f\u30a0-\u30ff]', '', text)
    # Удаляем корейский
    text = re.sub(r'[\uac00-\ud7af]', '', text)
    # Очищаем лишние пробелы
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def build_prompt(complaint_text, topic_group, subtopic, department, municipality):
    """Формирует промпт для генерации персонализированного черновика"""
    prompt = f"""<s>Ты — сотрудник администрации города Омска. Отвечай ТОЛЬКО на русском языке. Никаких других языков.

Напиши черновик ответа на жалобу жителя.

Правила:
1. ОТВЕЧАЙ ТОЛЬКО НА РУССКОМ ЯЗЫКЕ
2. Упомяни суть проблемы из жалобы (адрес, что именно случилось) — это персонализация
3. НЕ придумывай конкретные даты, сроки, имена сотрудников, номера документов
4. НЕ обещай конкретных результатов — только "принято в работу", "передано для рассмотрения"
5. Ответ должен быть вежливым и официальным
6. Это черновик — реальный сотрудник добавит конкретику

Примеры:

{TEMPLATE_EXAMPLES}

Теперь напиши черновик ответа на эту жалобу. ТОЛЬКО НА РУССКОМ ЯЗЫКЕ.

Тема: {topic_group}
Категория: {subtopic}
Отдел: {department}
Район: {municipality}

Текст жалобы: {complaint_text[:500]}

Черновик ответа (на русском):"""

    return prompt

def main():
    print("="*60)
    print("📄 ГЕНЕРАЦИЯ ЧЕРНОВИКОВ ОТВЕТОВ ЧЕРЕЗ LLM")
    print("="*60)
    
    # 1. Загружаем данные
    print("\n📂 Загрузка данных...")
    df = pd.read_excel(DATA_PATH, sheet_name="Лист1")
    df_test = df.head(10).copy()
    print(f"✅ Загружено {len(df_test)} тестовых записей")
    
    # 2. Очищаем текст
    df_test["Текст инцидента"] = df_test["Текст инцидента"].apply(clean_text)
    df_test["Группа тем"] = df_test["Группа тем"].fillna("Общее")
    df_test["Тема"] = df_test["Тема"].fillna("Обращение")
    df_test["Отдел"] = df_test["Отдел"].fillna("Администрация")
    df_test["Муниципалитет"] = df_test["Муниципалитет"].fillna("Омская область")
    
    # 3. Выбираем модель
    
    model_name = MODEL_QWEN_7B
    print(f"  Используем: {model_name}")
    
    # 4. Генерируем ответы
    print("\n" + "="*60)
    print("📝 ГЕНЕРАЦИЯ ОТВЕТОВ")
    print("="*60)
    
    results = []
    for idx, (_, row) in enumerate(df_test.iterrows()):
        complaint = str(row["Текст инцидента"])
        topic = str(row["Группа тем"])
        subtopic = str(row["Тема"])
        dept = str(row["Отдел"])
        municipality = str(row["Муниципалитет"])
        
        real_response = str(row.get("1ый ответ ПИ", ""))
        if pd.isna(real_response) or real_response == "nan":
            real_response = ""
        real_response = clean_text(real_response)
        
        print(f"\n--- Запись {idx+1}/20 ---")
        print(f"📢 Жалоба: {complaint[:150]}...")
        
        prompt = build_prompt(complaint, topic, subtopic, dept, municipality)
        
        try:
            response = generate(
                prompt=prompt,
                model_name=model_name,
                num_predict=256
            )
            response = remove_non_russian(response.strip())
        except Exception as e:
            response = f"[Ошибка генерации: {e}]"
            print(f"❌ Ошибка: {e}")
        
        print(f"🤖 Сгенерировано: {response[:200]}")
        if real_response:
            print(f"📋 Оригинал: {real_response[:200]}")
        print("-"*40)
        
        results.append({
            "id": idx,
            "complaint": complaint[:300],
            "generated_response": response,
            "real_response": real_response
        })
    
    # 5. Сохраняем
    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_PATH, index=False, encoding='utf-8-sig')
    print(f"\n💾 Результаты сохранены в {OUTPUT_PATH}")
    print(f"✅ Готово!")

if __name__ == "__main__":
    main()