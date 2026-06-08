import streamlit as st
import os
import pandas as pd
import time
import sys
import shutil
from pathlib import Path

# Импорт функций предобработки файлов
from run_pipeline import extract_and_clean

# Импорт LLM классификатора
from src.llm.batcher import create_batches
from src.llm.stage1_is_problem import classify_is_problem
from src.llm.stage2_topic import classify_topic
from src.llm.stage3_department import add_department_to_csv

PROJECT_ROOT = Path(__file__).resolve().parent.parent   
sys.path.insert(0, str(PROJECT_ROOT))

st.set_page_config(page_title="Classificator | Анализатор инцидентов", layout="wide")
st.title("🤖 LLM Классификатор инцидентов")

# ============ КОНФИГУРАЦИЯ ПУТЕЙ ============
LLM_INPUT_FILE = "data/raw/llm_input.xlsx"
LLM_TEMP_TOPICS_FILE = "data/processed/temp_topics.csv"
LLM_FINAL_OUTPUT_FILE = "data/processed/final_predictions.csv"
DEFAULT_TEST_FILE = "data/raw/text_classifier_data.xlsx"

# ============ БОКОВАЯ ПАНЕЛЬ ============
st.sidebar.header("Загрузка данных")

# Проверяем наличие файла для тестирования
use_default = False
if os.path.exists(DEFAULT_TEST_FILE):
    st.sidebar.success("✅ Файл для тестирования найден")
    use_default = st.sidebar.checkbox("Использовать файл для тестирования", value=True)

if not use_default:
    uploaded_file = st.sidebar.file_uploader("Загрузите свой файл (.xlsx)", type=["xlsx"], key="classifier_upload")
    if uploaded_file is not None:
        os.makedirs(os.path.dirname(LLM_INPUT_FILE), exist_ok=True)
        with open(LLM_INPUT_FILE, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.sidebar.success("✅ Файл загружен")
else:
    uploaded_file = True  # Флаг для использования стандартного файла
    st.sidebar.info("Используется файл для тестирования")

# ============ ОСНОВНОЙ КОНТЕНТ ============
st.write("Многоэтапная LLM-классификация инцидентов:")
st.write("1. **Этап 1** — определение is_problem")
st.write("2. **Этап 2** — определение topic")
st.write("3. **Этап 3** — определение department")

if st.button("▶️ Запустить классификацию", key="classifier_run"):
    if not uploaded_file:
        st.error("❌ Пожалуйста, сначала загрузите файл!")
    else:
        try:
            # ========== ЭТАП 0: Очистка ==========
            st.info("⏳ Этап 0: Загрузка и очистка данных...")
            
            # Если используем стандартный файл, копируем его
            if use_default:
                shutil.copy(DEFAULT_TEST_FILE, "data/raw/test_40.xlsx")
            else:
                shutil.copy(LLM_INPUT_FILE, "data/raw/test_40.xlsx")
            
            cleaned_df = extract_and_clean()
            st.success("✅ Данные очищены")
            
            # Подготовка (используем путь из run_pipeline.py)
            df = pd.read_csv("data/processed/test_40_cleaned.csv").head(5)
            df["incident_id"] = range(len(df))
            records = df.to_dict(orient="records")
            
            # ========== ЭТАП 1: is_problem ==========
            st.info("⏳ Этап 1: Определение is_problem...")
            all_problems = []
            progress_bar_1 = st.progress(0)
            
            batches_list = list(create_batches(records, batch_size=5))
            for batch_number, batch in enumerate(batches_list, start=1):
                progress = batch_number / len(batches_list)
                progress_bar_1.progress(progress)
                
                try:
                    result = classify_is_problem(batch)
                    all_problems.extend(result)
                    time.sleep(1)
                except Exception as e:
                    st.warning(f"⚠️ Ошибка батча {batch_number}: {e}")
                    for row in batch:
                        all_problems.append({
                            "incident_id": row["incident_id"],
                            "is_problem": 1
                        })
            
            problem_df = pd.DataFrame(all_problems)
            df = df.merge(problem_df, on="incident_id", how="left")
            st.success("✅ Этап 1 завершен")
            
            # ========== ЭТАП 2: topic ==========
            st.info("⏳ Этап 2: Определение темы для ВСЕХ записей...")
            all_topics = []
            progress_bar_2 = st.progress(0)
            
            batches_list = list(create_batches(records, batch_size=5))
            for batch_number, batch in enumerate(batches_list, start=1):
                progress = batch_number / len(batches_list)
                progress_bar_2.progress(progress)
                
                try:
                    result = classify_topic(batch)
                    all_topics.extend(result)
                    time.sleep(1)
                except Exception as e:
                    st.warning(f"⚠️ Ошибка батча {batch_number}: {e}")
                    for row in batch:
                        all_topics.append({
                            "incident_id": row["incident_id"],
                            "topic": "Прочее"
                        })
            
            topic_df = pd.DataFrame(all_topics)
            df = df.merge(topic_df, on="incident_id", how="left")
            df['topic'] = df['topic'].fillna("Прочее")
            
            os.makedirs(os.path.dirname(LLM_TEMP_TOPICS_FILE), exist_ok=True)
            df.to_csv(LLM_TEMP_TOPICS_FILE, index=False, encoding="utf-8-sig")
            st.success("✅ Этап 2 завершен")
            
            # ========== ЭТАП 3: department ==========
            st.info("⏳ Этап 3: Определение отдела...")
            add_department_to_csv(LLM_TEMP_TOPICS_FILE, LLM_FINAL_OUTPUT_FILE)
            st.success("✅ Этап 3 завершен")
            
            st.success("🎉 Классификация успешно завершена!")
            
            # Предоставить скачивание
            if os.path.exists(LLM_FINAL_OUTPUT_FILE):
                with open(LLM_FINAL_OUTPUT_FILE, "rb") as f:
                    st.download_button(
                        label="📥 Скачать результаты классификации (final_predictions.csv)",
                        data=f.read(),
                        file_name="final_predictions.csv",
                        mime="text/csv"
                    )
                
                # Показать превью
                st.subheader("📋 Превью результатов")
                result_df = pd.read_csv(LLM_FINAL_OUTPUT_FILE)
                st.dataframe(result_df.head(10), use_container_width=True)
                    
        except Exception as e:
            st.error(f"❌ Критическая ошибка: {e}")
            import traceback
            st.text(traceback.format_exc())
