import streamlit as st
import os
import pandas as pd
import re
import time
import sys
from pathlib import Path
from openpyxl import load_workbook

PROJECT_ROOT = Path(__file__).resolve().parent.parent   
sys.path.insert(0, str(PROJECT_ROOT))

from src.llm.llama_client import generate

st.set_page_config(page_title="Generator | Анализатор инцидентов", layout="wide")
st.title("✉️ Генератор ответов на обращения")

LLM_INPUT_FILE = "data/raw/generator_input.xlsx"
LLM_OUTPUT_FILE = "data/processed/llm_responses.csv"
DEFAULT_TEST_FILE = "data/raw/text_classifier_data.xlsx"

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

def clean_text(text):
    """Очищает текст от специальных символов и форматирования"""
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
    """Удаляет не-русские символы (иероглифы, иероглифы и т.д.)"""
    if not isinstance(text, str):
        return text
    text = re.sub(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]', '', text)
    text = re.sub(r'[\u3040-\u309f\u30a0-\u30ff]', '', text)
    text = re.sub(r'[\uac00-\ud7af]', '', text)
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

st.sidebar.header("Загрузка данных")

use_default = False
if os.path.exists(DEFAULT_TEST_FILE):
    st.sidebar.success("✅ Файл для тестирования найден")
    use_default = st.sidebar.checkbox("Использовать файл для тестирования", value=True)

if not use_default:
    uploaded_file = st.sidebar.file_uploader("Загрузите свой файл (.xlsx)", type=["xlsx"], key="generator_upload")
    if uploaded_file is not None:
        os.makedirs(os.path.dirname(LLM_INPUT_FILE), exist_ok=True)
        with open(LLM_INPUT_FILE, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.sidebar.success("✅ Файл загружен")
else:
    uploaded_file = True
    st.sidebar.info("Используется файл для тестирования")

st.write("Генерация персонализированных черновиков ответов на обращения граждан с использованием LLM")

if st.button("▶️ Запустить генерацию", key="generator_run"):
    if not uploaded_file:
        st.error("❌ Пожалуйста, сначала загрузите файл!")
    else:
        try:
            st.info("⏳ Загрузка данных...")
            
            if use_default:
                input_file_path = DEFAULT_TEST_FILE
            else:
                input_file_path = LLM_INPUT_FILE
            
            df = load_excel_simple(input_file_path)
            df_test = df.head(5).copy()
            
            st.success("✅ Данные загружены")
            
            st.subheader("📋 Полный тестовый датасет")
            st.dataframe(df_test, use_container_width=True)
        
            df_test["Текст инцидента"] = df_test["Текст инцидента"].apply(clean_text)
            df_test["Группа тем"] = df_test["Группа тем"].fillna("Общее") if "Группа тем" in df_test.columns else "Общее"
            df_test["Тема"] = df_test["Тема"].fillna("Обращение") if "Тема" in df_test.columns else "Обращение"
            df_test["Отдел"] = df_test["Отдел"].fillna("Администрация") if "Отдел" in df_test.columns else "Администрация"
            df_test["Муниципалитет"] = df_test["Муниципалитет"].fillna("Омская область") if "Муниципалитет" in df_test.columns else "Омская область"
            
            
            st.info("⏳ Генерация ответов (это может занять время)...")
            results = []
            progress_bar = st.progress(0)
            
            for idx, (_, row) in enumerate(df_test.iterrows()):
                progress = (idx + 1) / len(df_test)
                progress_bar.progress(progress)
                
                complaint = str(row["Текст инцидента"])
                topic = str(row.get("Группа тем", "Общее"))
                subtopic = str(row.get("Тема", "Обращение"))
                dept = str(row.get("Отдел", "Администрация"))
                municipality = str(row.get("Муниципалитет", "Омская область"))
                
                real_response = str(row.get("1ый ответ ПИ", ""))
                if pd.isna(real_response) or real_response == "nan":
                    real_response = ""
                real_response = clean_text(real_response)
                
                try:
                    prompt = build_prompt(complaint, topic, subtopic, dept, municipality)
                    response = generate(prompt=prompt)
                    response = remove_non_russian(response.strip())
                except Exception as e:
                    response = f"[Ошибка генерации: {e}]"
                    st.warning(f"⚠️ Ошибка на строке {idx + 1}: {e}")
                
                results.append({
                    "id": idx,
                    "complaint": complaint[:300],
                    "generated_response": response,
                    "real_response": real_response
                })
            
            results_df = pd.DataFrame(results)
            
            if "real_response" in results_df.columns:
                results_df = results_df.drop(columns=["real_response"])
            elif "id" in results_df.columns:
                results_df = results_df.drop(columns=["id"])


            
            os.makedirs(os.path.dirname(LLM_OUTPUT_FILE), exist_ok=True)
            results_df.to_csv(LLM_OUTPUT_FILE, index=False, encoding='utf-8-sig')
            
            st.success("🎉 Генерация успешно завершена!")
            if "id" in df.columns:
                df = df.drop(columns=["id"])

            if os.path.exists(LLM_OUTPUT_FILE):
                with open(LLM_OUTPUT_FILE, "rb") as f:
                    st.download_button(
                        label="📥 Скачать результаты генерации (llm_responses.csv)",
                        data=f.read(),
                        file_name="llm_responses.csv",
                        mime="text/csv"
                    )
                
                st.subheader("📋 Превью результатов")
                st.dataframe(results_df, use_container_width=True)
                    
        except Exception as e:
            st.error(f"❌ Критическая ошибка: {e}")
            import traceback
            st.text(traceback.format_exc())
