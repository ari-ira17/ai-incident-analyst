import streamlit as st
import os
import pandas as pd
import time
import sys
import shutil
import json
from pathlib import Path
from openpyxl import load_workbook

# Импорт функций предобработки файлов
from run_pipeline import extract_and_clean

# Импорт LLM классификатора
from src.llm.batcher import create_batches
from src.llm.stage1_is_problem import classify_is_problem
from src.llm.stage2_topic import classify_topic
from src.llm.stage3_department import add_department_to_csv
from src.preprocessing.cleaner import IncidentDataCleaner

PROJECT_ROOT = Path(__file__).resolve().parent.parent   
sys.path.insert(0, str(PROJECT_ROOT))

st.set_page_config(page_title="Classificator | Анализатор инцидентов", layout="wide")
st.title("🤖 LLM Классификатор инцидентов")

# ============ КОНФИГУРАЦИЯ ПУТЕЙ ============
LLM_INPUT_FILE = "data/raw/llm_input.xlsx"
LLM_TEMP_TOPICS_FILE = "data/processed/temp_topics.csv"
LLM_FINAL_OUTPUT_CSV = "data/processed/final_predictions.csv"
LLM_FINAL_OUTPUT_FILE = "data/processed/final_predictions.xlsx"
DEFAULT_TEST_FILE = "data/raw/text_classifier_data.xlsx"

# ============ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ============
def load_excel_simple(file_path: str) -> pd.DataFrame:
    """Загружает Excel файл с любой структурой столбцов"""
    wb = load_workbook(file_path, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    headers = [str(x).strip() if x else "" for x in rows[0]]
    data = []
    for row in rows[1:]:
        record = {h: row[i] if i < len(row) else None for i, h in enumerate(headers)}
        data.append(record)
    return pd.DataFrame(data)

def prepare_classifier_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Преобразует датасет в формат, совместимый с LLM классификатором.
    Если есть только "Текст инцидента", добавляет необходимые столбцы.
    """
    # Копируем исходный датасет
    result_df = df.copy()
    
    # Проверяем наличие столбца "Текст инцидента"
    if "Текст инцидента" not in result_df.columns:
        st.error("❌ Датасет должен содержать столбец 'Текст инцидента'")
        return None
    
    # Добавляем недостающие столбцы с пустыми значениями
    required_cols = ["Отдел", "Тема", "Муниципалитет", "Тип инцидента"]
    for col in required_cols:
        if col not in result_df.columns:
            result_df[col] = ""
    
    # Добавляем ID если нет
    if "incident_id" not in result_df.columns:
        result_df["incident_id"] = range(len(result_df))
    
    # Очищаем текст (удаляем пропуски, нормализуем)
    result_df["Текст инцидента"] = result_df["Текст инцидента"].fillna("").astype(str).str.strip()
    
    return result_df

def safe_parse_llm_result(result):
    """
    Безопасно парсит результат классификации.
    Может быть JSON-строкой или списком словарей.
    """
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict):
                return [parsed]
        except (json.JSONDecodeError, TypeError):
            pass
    elif isinstance(result, list):
        return result
    
    return []

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
            st.info("⏳ Этап 0: Загрузка данных...")
            
            if use_default:
                input_file_path = DEFAULT_TEST_FILE
            else:
                input_file_path = LLM_INPUT_FILE
            
            df = load_excel_simple(input_file_path)
            st.write(f"Загружено строк: {len(df)}")
            
            df = prepare_classifier_data(df)
            if df is None:
                raise ValueError("Невозможно подготовить данные")
            
            st.success("✅ Данные загружены и подготовлены")
            
            st.subheader("📋 Полный тестовый датасет")
            st.dataframe(df[["Текст инцидента"]], use_container_width=True)

            df_for_records = df.head(20).copy()
            if "incident_id" not in df_for_records.columns:
                df_for_records["incident_id"] = range(len(df_for_records))
            records = df_for_records.to_dict(orient="records")
            
            st.info("⏳ Этап 1: Определение is_problem...")
            all_problems = []
            progress_bar_1 = st.progress(0)

            batches_list = list(create_batches(records, batch_size=5))
            for batch_number, batch in enumerate(batches_list, start=1):
                progress = batch_number / len(batches_list)
                progress_bar_1.progress(progress)

                try:
                    result = classify_is_problem(batch)
                    parsed = safe_parse_llm_result(result)

                    for i, item in enumerate(parsed):
                        if "incident_id" not in item:
                            item["incident_id"] = batch[i].get("incident_id", i)
                    all_problems.extend(parsed)

                except Exception as e:
                    st.warning(f"⚠️ Ошибка батча {batch_number}: {e}")
                    for i, row in enumerate(batch):
                        all_problems.append({
                            "incident_id": row.get("incident_id", i),
                            "is_problem": 1
                        })

            if all_problems:
                problem_df = pd.DataFrame(all_problems)
            else:
                problem_df = pd.DataFrame(columns=["incident_id", "is_problem"])

            if "incident_id" not in problem_df.columns:
                problem_df = pd.DataFrame({
                    "incident_id": [rec["incident_id"] for rec in records],
                    "is_problem": 1
                })

            problem_df = problem_df.drop_duplicates(subset=["incident_id"], keep="first")

            df_merged = pd.DataFrame(records).merge(problem_df, on="incident_id", how="left")

            df_merged["is_problem"] = df_merged["is_problem"].fillna(1).astype(int)
            
            st.info("⏳ Этап 2: Определение темы каждой записи...")
            all_topics = []
            progress_bar_2 = st.progress(0)
            
            batches_list = list(create_batches(records, batch_size=5))
            for batch_number, batch in enumerate(batches_list, start=1):
                progress = batch_number / len(batches_list)
                progress_bar_2.progress(progress)
                
                try:
                    result = classify_topic(batch)
                    parsed_result = safe_parse_llm_result(result)
                    for i, item in enumerate(parsed_result):
                        if "incident_id" not in item and i < len(batch):
                            item["incident_id"] = batch[i].get("incident_id", i)
                    all_topics.extend(parsed_result)
                    time.sleep(1)
                except Exception as e:
                    st.warning(f"⚠️ Ошибка батча {batch_number}: {e}")
                    for i, row in enumerate(batch):
                        all_topics.append({
                            "incident_id": row.get("incident_id", i),
                            "topic": "Прочее"
                        })
            
            topic_df = pd.DataFrame(all_topics)
            topic_df = topic_df.drop_duplicates(subset=["incident_id"], keep="first")
            
            df_merged = df_merged.merge(topic_df, on="incident_id", how="left")
            df_merged['topic'] = df_merged['topic'].fillna("Прочее")
            
            
            st.info("⏳ Этап 3: Определение отдела")
            os.makedirs(os.path.dirname(LLM_TEMP_TOPICS_FILE), exist_ok=True)
            df_merged.to_csv(LLM_TEMP_TOPICS_FILE, index=False, encoding="utf-8-sig")
            
            add_department_to_csv(LLM_TEMP_TOPICS_FILE, LLM_FINAL_OUTPUT_CSV)
            
            result_df = pd.read_csv(LLM_FINAL_OUTPUT_CSV)
            with pd.ExcelWriter(LLM_FINAL_OUTPUT_FILE, engine="openpyxl") as writer:
                result_df.to_excel(writer, sheet_name="Результаты", index=False)
            
            st.success("🎉 Классификация успешно завершена!")
            
            if os.path.exists(LLM_FINAL_OUTPUT_FILE):
                result_df = pd.read_excel(LLM_FINAL_OUTPUT_FILE)
                
                output_columns = ["Текст инцидента", "is_problem", "topic", "department"]
                available_columns = [col for col in output_columns if col in result_df.columns]
                result_df_output = result_df[available_columns]
                
                with open(LLM_FINAL_OUTPUT_FILE, "rb") as f:
                    st.download_button(
                        label="📥 Скачать результаты классификации (final_predictions.xlsx)",
                        data=f.read(),
                        file_name="final_predictions.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                st.subheader("📋 Превью результатов")
                st.dataframe(result_df_output, use_container_width=True)
                    
        except Exception as e:
            st.error(f"❌ Критическая ошибка: {e}")
            import traceback
            st.text(traceback.format_exc())
