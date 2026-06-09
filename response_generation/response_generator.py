# ============================================
# ПОЛНЫЙ ИСПРАВЛЕННЫЙ КОД ДЛЯ ОБУЧЕНИЯ МОДЕЛИ
# ============================================

import pandas as pd
import re
import torch
import os
from sklearn.model_selection import train_test_split
from transformers import (
    AutoTokenizer, 
    AutoModelForSeq2SeqLM, 
    Trainer, 
    TrainingArguments,
    DataCollatorForSeq2Seq
)
from datasets import Dataset
import numpy as np
import logging

# Отключаем лишние предупреждения
logging.getLogger("transformers").setLevel(logging.ERROR)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Для воспроизводимости результатов
torch.manual_seed(42)
np.random.seed(42)

# ============================================
# ПУТЬ К ВАШЕМУ ФАЙЛУ (СОХРАНЯЕМ)
# ============================================
DATA_PATH = "data/raw/test_40.xlsx"  # <- ПУТЬ К ВАШЕМУ ФАЙЛУ
MODEL_OUTPUT_DIR = "./admin_response_model"
DEFAULT_MODEL = "cointegrated/rut5-base"

# ============================================
# 2.2 ЗАГРУЗКА И ПОДГОТОВКА ДАННЫХ
# ============================================

def load_and_prepare_data(file_path):
    """Загрузка и очистка данных из Excel"""
    print("📂 Загрузка данных...")
    print(f"   Путь к файлу: {file_path}")
    print(f"   Абсолютный путь: {os.path.abspath(file_path)}")
    
    df = pd.read_excel(file_path, sheet_name="Лист1")
    
    # Отбираем успешно завершённые инциденты с непустым ответом
    df = df[
        (df["Текущий шаг инцидента"] == "Готово") &
        (df["1ый ответ ПИ"].notna()) &
        (df["1ый ответ ПИ"] != "") &
        (df["Текст инцидента"].notna())
    ].copy()
    
    print(f"✅ Найдено {len(df)} записей с ответами")
    
    # Очистка текстов
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
    
    df["Текст инцидента"] = df["Текст инцидента"].apply(clean_text)
    df["1ый ответ ПИ"] = df["1ый ответ ПИ"].apply(clean_text)
    
    # Удаляем слишком короткие ответы
    df = df[df["1ый ответ ПИ"].str.len() > 10]
    
    # Заполняем пропуски
    df["Группа тем"] = df["Группа тем"].fillna("Общее")
    df["Тема"] = df["Тема"].fillna("Обращение")
    df["Отдел"] = df["Отдел"].fillna("Администрация")
    df["Муниципалитет"] = df["Муниципалитет"].fillna("Омская область")
    
    return df

def create_model_inputs(df):
    """Создание входных и выходных последовательностей"""
    
    def make_input(row):
        complaint = row['Текст инцидента'][:400]
        # Используем префикс "summarize:" — rut5-base знает этот формат
        return f"summarize: тема {row['Группа тем']} категория {row['Тема']} отдел {row['Отдел']} район {row['Муниципалитет']} текст {complaint}"
    
    def make_output(row):
        return row["1ый ответ ПИ"]
    
    df["input_text"] = df.apply(make_input, axis=1)
    df["target_text"] = df.apply(make_output, axis=1)
    
    # Удаляем слишком длинные последовательности
    df = df[df["input_text"].str.len() < 600]
    df = df[df["target_text"].str.len() < 300]
    
    return df

# ============================================
# 2.3 НАСТРОЙКА МОДЕЛИ
# ============================================

def setup_model(model_name=DEFAULT_MODEL):
    """Инициализация токенизатора и модели"""
    print(f"🤖 Загрузка модели {model_name}...")
    
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=True
    )
    
    model = AutoModelForSeq2SeqLM.from_pretrained(
        model_name,
        trust_remote_code=True
    )
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    print(f"✅ Модель загружена: {model_name}")
    
    if torch.cuda.is_available():
        model = model.cuda()
        print("✅ Модель на GPU")
    
    return tokenizer, model

def preprocess_function(examples, tokenizer, max_input_length=384, max_target_length=192):
    """Токенизация данных"""
    inputs = tokenizer(
        examples["input_text"],
        max_length=max_input_length,
        truncation=True,
        padding="max_length",
        return_tensors=None
    )
    
    targets = tokenizer(
        examples["target_text"],
        max_length=max_target_length,
        truncation=True,
        padding="max_length",
        return_tensors=None
    )
    
    inputs["labels"] = targets["input_ids"]
    return inputs

# ============================================
# 2.4 ОБУЧЕНИЕ МОДЕЛИ
# ============================================

def train_model(df, tokenizer, model, output_dir="./admin_response_model"):
    """Обучение модели"""
    
    train_df, val_df = train_test_split(
        df[["input_text", "target_text"]], 
        test_size=0.15,
        random_state=42,
        shuffle=True
    )
    
    print(f"📊 Обучающая выборка: {len(train_df)} примеров")
    print(f"📊 Валидационная выборка: {len(val_df)} примеров")
    
    train_dataset = Dataset.from_pandas(train_df)
    val_dataset = Dataset.from_pandas(val_df)
    
    def preprocess_with_args(examples):
        return preprocess_function(examples, tokenizer)
    
    train_tokenized = train_dataset.map(
        preprocess_with_args, 
        batched=True, 
        remove_columns=train_dataset.column_names
    )
    val_tokenized = val_dataset.map(
        preprocess_with_args, 
        batched=True, 
        remove_columns=val_dataset.column_names
    )
    
    data_collator = DataCollatorForSeq2Seq(
        tokenizer=tokenizer,
        model=model,
        padding=True
    )
    
    training_args = TrainingArguments(
        output_dir=output_dir,
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=3e-4,
        per_device_train_batch_size=2,
        per_device_eval_batch_size=2,
        num_train_epochs=10,  # Увеличили с 5 до 10
        weight_decay=0.01,
        logging_dir=f"{output_dir}/logs",
        logging_steps=50,
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        fp16=torch.cuda.is_available(),
        dataloader_num_workers=0,
        warmup_steps=100,
        report_to="none",
        gradient_accumulation_steps=2,
    )
    
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_tokenized,
        eval_dataset=val_tokenized,
        data_collator=data_collator
    )
    
    print("🚀 Начинаем обучение...")
    trainer.train()
    
    final_path = f"{output_dir}_final"
    print(f"💾 Сохраняем модель в {final_path}")
    model.save_pretrained(final_path)
    tokenizer.save_pretrained(final_path)
    
    return trainer

# ============================================
# 2.5 ГЕНЕРАЦИЯ ОТВЕТОВ
# ============================================

def generate_response(model, tokenizer, complaint_text, topic_group="Дороги",
                     subtopic="Уборка дорог от снега и наледи",
                     department="Департамент городского хозяйства (ДГХ)",
                     municipality="Омск г.о."):
    """Генерация ответа на новую жалобу"""
    model.eval()
    
    complaint_short = complaint_text[:400]
    # Используем тот же префикс, что и при обучении
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
            temperature=0.3,  # Понизили температуру для более детерминированных ответов
            top_p=0.85,
            do_sample=False,  # Убрали sampling — для T5 лучше beam search
            early_stopping=True,
            no_repeat_ngram_size=3,
            repetition_penalty=1.2
        )
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True, clean_up_tokenization_spaces=True)
    
    # Удаляем остаточные <extra_id_*> если они есть
    response = re.sub(r'<extra_id_\d+>', '', response).strip()
    
    if len(response) == 0:
        response = "Ваше обращение принято. Будет рассмотрено в установленном порядке."
    
    return response

# ============================================
# 3. ОСНОВНОЙ СКРИПТ
# ============================================

def main():
    """Главная функция"""
    print("="*60)
    print("🤖 ОБУЧЕНИЕ МОДЕЛИ ГЕНЕРАЦИИ ОТВЕТОВ")
    print("="*60)
    
    # Проверяем наличие файла
    if not os.path.exists(DATA_PATH):
        print(f"❌ Файл {DATA_PATH} не найден!")
        print(f"   Текущая директория: {os.getcwd()}")
        print("   Пожалуйста, проверьте путь к файлу")
        return
    
    # Загрузка данных
    df = load_and_prepare_data(DATA_PATH)
    df = create_model_inputs(df)
    
    if len(df) < 10:
        print(f"⚠️ Недостаточно данных! Нужно минимум 10 примеров.")
        print(f"   Доступно: {len(df)} примеров")
        return
    
    print(f"\n📊 Итоговый размер выборки: {len(df)} примеров")
    
    # Загрузка модели
    tokenizer, model = setup_model(DEFAULT_MODEL)
    
    # Обучение
    trainer = train_model(df, tokenizer, model, MODEL_OUTPUT_DIR)
    
    # Тестирование
    print("\n" + "="*60)
    print("📝 ТЕСТИРОВАНИЕ МОДЕЛИ")
    print("="*60)
    
    test_complaints = [
        ("Улица Ленина, 15, уже неделю не чистят снег", "Дороги", "Уборка дорог от снега и наледи", "Департамент городского хозяйства (ДГХ)"),
        ("В квартире холодно, батареи еле теплые", "ЖКХ", "Ненадлежащее качество или отключение отопления", "Администрация города Омска"),
    ]
    
    for complaint, topic, subtopic, dept in test_complaints:
        response = generate_response(model, tokenizer, complaint, topic, subtopic, dept)
        print(f"\n📢 Жалоба: {complaint}")
        print(f"📝 Ответ: {response}...")
        print("-"*40)
    
    print(f"\n✅ Модель сохранена в: {MODEL_OUTPUT_DIR}_final")

# ============================================
# ЗАПУСК
# ============================================

if __name__ == "__main__":
    main()