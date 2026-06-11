import streamlit as st
import os
import pandas as pd
import re
import sys
from pathlib import Path
from openpyxl import load_workbook

PROJECT_ROOT = Path(__file__).resolve().parent.parent   
sys.path.insert(0, str(PROJECT_ROOT))

from src.llm.llama_client import generate
from src.workspace import render_workspace_panel, init_workspace, get_workspace, set_workspace_file, FileManager

st.set_page_config(page_title="Generator | Анализатор инцидентов", layout="wide")

# CSS только для базового оформления (без сложных классов)
st.markdown("""
<style>
.page-header {
    margin-bottom: 2rem;
}
.page-badge {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    background: rgba(15,98,254,.08);
    color: #0f62fe;
    font-size: .75rem;
    font-weight: 700;
    letter-spacing: .08em;
    margin-bottom: .8rem;
}
.title-row {
    display: flex;
    align-items: center;
    gap: 14px;
}
.title-bar {
    width: 5px;
    height: 44px;
    background: #0f62fe;
    border-radius: 3px;
    flex-shrink: 0;
}
.page-title {
    font-size: 2.2rem;
    font-weight: 700;
    margin: 0;
    line-height: 1.1;
}
.page-subtitle {
    margin-top: .8rem;
    color: gray;
    font-size: 1rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid rgba(120,120,120,.2);
}
</style>
""", unsafe_allow_html=True)

# Хедер страницы
st.markdown("""
<div class="page-header">
    <div class="page-badge">
        RESPONSE GENERATOR MODULE
    </div>
    <div class="title-row">
        <div class="title-bar"></div>
        <h1 class="page-title">
            Генератор ответов на обращения
        </h1>
    </div>
    <div class="page-subtitle">
        LLM формирует официальные черновики ответов на обращения граждан на основе классификации инцидентов
    </div>
</div>
""", unsafe_allow_html=True)

init_workspace()

left_col, right_col = st.columns([3, 1])

with right_col:
    render_workspace_panel(active_page="generator")

with left_col:
    fm = FileManager()

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
        """Удаляет не-русские символы (иероглифы и т.д.)"""
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

    # Блок описания процесса (простой, без сложного HTML)
    st.markdown("---")
    st.markdown("### ⚙️ Как работает генератор")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div style="background: var(--secondary-background-color); border-radius: 12px; padding: 1rem; text-align: center; border: 1px solid rgba(15,98,254,.2);">
            <div style="font-size: 1.8rem; font-weight: 700; color: #0f62fe;">1</div>
            <div style="font-weight: 700;">Подготовка данных</div>
            <div style="font-size: 0.8rem; opacity: 0.7;">Очистка и нормализация обращений</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style="background: var(--secondary-background-color); border-radius: 12px; padding: 1rem; text-align: center; border: 1px solid rgba(15,98,254,.2);">
            <div style="font-size: 1.8rem; font-weight: 700; color: #0f62fe;">2</div>
            <div style="font-weight: 700;">Формирование промпта</div>
            <div style="font-size: 0.8rem; opacity: 0.7;">Добавление темы, отдела и контекста</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div style="background: var(--secondary-background-color); border-radius: 12px; padding: 1rem; text-align: center; border: 1px solid rgba(15,98,254,.2);">
            <div style="font-size: 1.8rem; font-weight: 700; color: #0f62fe;">3</div>
            <div style="font-weight: 700;">Генерация LLM</div>
            <div style="font-size: 0.8rem; opacity: 0.7;">Создание официального ответа</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")

    ws = get_workspace()
    classified_file_path = ws.get("classified_file")

    if classified_file_path is None:
        st.info("⬅️ Выберите классифицированный файл в правой панели Workspace (папка «Классифицированные»).")
    else:
        st.success(f"✅ Выбран файл: `{os.path.basename(classified_file_path)}`")

        if st.button("▶️ Запустить генерацию", key="generator_run", type="primary"):
            try:
                st.info("⏳ Загрузка данных...")
                
                df = load_excel_simple(classified_file_path)
                df_test = df.head(5).copy()
                
                st.success("✅ Данные загружены")
                
                st.subheader("📋 Тестовый датасет (первые 5 строк)")
                st.dataframe(df_test, use_container_width=True)
            
                df_test["Текст инцидента"] = df_test["Текст инцидента"].apply(clean_text)
                df_test["Группа тем"] = df_test["Группа тем"].fillna("Общее") if "Группа тем" in df_test.columns else "Общее"
                df_test["Тема"] = df_test["Тема"].fillna("Обращение") if "Тема" in df_test.columns else "Обращение"
                df_test["Отдел"] = df_test["Отдел"].fillna("Администрация") if "Отдел" in df_test.columns else "Администрация"
                df_test["Муниципалитет"] = df_test["Муниципалитет"].fillna("Омская область") if "Муниципалитет" in df_test.columns else "Омская область"
                
                # Прогресс-бар и статус
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                results = []
                
                for idx, (_, row) in enumerate(df_test.iterrows()):
                    progress = (idx + 1) / len(df_test)
                    progress_bar.progress(progress)
                    status_text.text(f"🔄 Генерация ответа {idx + 1} из {len(df_test)}...")
                    
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
                        "Текст инцидента": complaint[:300],
                        "Сгенерированный ответ": response,
                        "Оригинальный ответ": real_response if real_response else "Нет данных"
                    })
                
                status_text.empty()
                progress_bar.empty()
                
                results_df = pd.DataFrame(results)
                
                # Сохраняем результат
                base_name = os.path.splitext(os.path.basename(classified_file_path))[0]
                generated_filename = f"{base_name}_responses.xlsx"
                generated_path = fm.get_output_path("generated", generated_filename)
                
                results_df.to_excel(generated_path, index=False, engine='openpyxl')
                
                set_workspace_file("generated", generated_path)
                
                st.success("🎉 Генерация успешно завершена!")

                # Кнопка скачивания
                if os.path.exists(generated_path):
                    with open(generated_path, "rb") as f:
                        st.download_button(
                            label=f"📥 Скачать результаты генерации ({generated_filename})",
                            data=f.read(),
                            file_name=generated_filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                    
                    st.markdown("### 📄 Результаты генерации")
                    st.dataframe(results_df, use_container_width=True)
                        
            except Exception as e:
                st.error(f"❌ Критическая ошибка: {e}")
                import traceback
                st.text(traceback.format_exc())