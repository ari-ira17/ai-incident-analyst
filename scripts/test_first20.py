# ============================================
# ТЕСТИРОВАНИЕ ОБУЧЕННОЙ МОДЕЛИ НА ПЕРВЫХ 20 СТРОКАХ
# ============================================

import pandas as pd
import re
import torch
import os
from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM
)
import logging

logging.getLogger("transformers").setLevel(logging.ERROR)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

DATA_PATH = "data/raw/testovy_fayl.xlsx"
MODEL_PATH = "./admin_response_model_final"

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

def generate_response(model, tokenizer, complaint_text, topic_group="Общее",
                     subtopic="Обращение",
                     department="Администрация",
                     municipality="Омская область"):
    """Генерация ответа на новую жалобу (из response_generator.py)"""
    model.eval()
    
    complaint_short = complaint_text[:400]
    # Тот же префикс, что и при обучении
    input_text = f"summarize: тема {topic_group} категория {subtopic} отдел {department} район {municipality} текст {complaint_short}"
    
    inputs = tokenizer(
        input_text,
        return_tensors="pt",
        max_length=384,
        truncation=True,
        padding=True
    )
    
    if torch.cuda.is_available():
        inputs = {k: v.cuda() for k, v in inputs.items()}
    
    with torch.no_grad():
        outputs = model.generate(
            inputs["input_ids"],
            max_length=192,
            min_length=10,
            num_beams=4,
            temperature=0.3,
            top_p=0.85,
            do_sample=False,
            early_stopping=True,
            no_repeat_ngram_size=3,
            repetition_penalty=1.2
        )
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True, clean_up_tokenization_spaces=True)
    response = re.sub(r'<extra_id_\d+>', '', response).strip()
    
    if len(response) == 0:
        response = "Ваше обращение принято. Будет рассмотрено в установленном порядке."
    
    return response

def main():
    print("="*60)
    print("🧪 ТЕСТИРОВАНИЕ МОДЕЛИ НА ПЕРВЫХ 20 СТРОКАХ")
    print("="*60)
    
    # 1. Загружаем данные
    print("\n📂 Загрузка данных...")
    df = pd.read_excel(DATA_PATH, sheet_name="Лист1")
    
    # Берём первые 20 строк
    df_test = df.head(20).copy()
    print(f"✅ Загружено {len(df_test)} тестовых записей")
    
    # 2. Очищаем текст как в response_generator
    df_test["Текст инцидента"] = df_test["Текст инцидента"].apply(clean_text)
    
    # Заполняем пропуски как в response_generator
    df_test["Группа тем"] = df_test["Группа тем"].fillna("Общее")
    df_test["Тема"] = df_test["Тема"].fillna("Обращение")
    df_test["Отдел"] = df_test["Отдел"].fillna("Администрация")
    df_test["Муниципалитет"] = df_test["Муниципалитет"].fillna("Омская область")
    
    # 3. Загружаем обученную модель
    print(f"\n🤖 Загрузка модели из {MODEL_PATH}...")
    
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Модель не найдена по пути: {MODEL_PATH}")
        print(f"   Текущая директория: {os.getcwd()}")
        return
    
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH, trust_remote_code=True)
    
    if torch.cuda.is_available():
        model = model.cuda()
        print("✅ Модель на GPU")
    else:
        print("✅ Модель на CPU")
    
    # 4. Генерируем ответы для каждой строки
    print("\n" + "="*60)
    print("📝 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("="*60)
    
    results = []
    for idx, row in df_test.iterrows():
        complaint = str(row["Текст инцидента"])[:200]
        
        response = generate_response(
            model, tokenizer,
            complaint_text=str(row["Текст инцидента"]),
            topic_group=str(row["Группа тем"]),
            subtopic=str(row["Тема"]),
            department=str(row["Отдел"]),
            municipality=str(row["Муниципалитет"])
        )
        
        # Берём реальный ответ для сравнения (если есть)
        real_response = str(row.get("1ый ответ ПИ", ""))[:200] if pd.notna(row.get("1ый ответ ПИ")) else "(нет ответа)"
        
        results.append({
            "id": idx,
            "complaint": complaint[:150],
            "generated_response": response[:200],
            "real_response": real_response[:200]
        })
        
        print(f"\n--- Запись {idx+1} ---")
        print(f"📢 Жалоба: {complaint[:150]}")
        print(f"🤖 Сгенерировано: {response[:200]}")
        print(f"📋 Оригинал: {real_response[:200]}")
        print("-"*40)
    
    # 5. Сохраняем результаты
    results_df = pd.DataFrame(results)
    output_path = "test_results_first20.csv"
    results_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n💾 Результаты сохранены в {output_path}")
    print(f"✅ Тестирование завершено!")

if __name__ == "__main__":
    main()