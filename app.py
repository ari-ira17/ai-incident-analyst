import streamlit as st
import os

from src.workspace import render_workspace_panel, init_workspace

st.set_page_config(page_title="AI-аналитик инцидентов | Цифровой прорыв", layout="wide")

# Инициализация workspace
init_workspace()

# Основной контент (слева) и workspace (справа)
left_col, right_col = st.columns([3, 1])

with right_col:
    render_workspace_panel()

with left_col:
    st.title("🏢 AI-аналитик инцидентов")
    st.markdown("### Решение кейса в рамках конкурса **Цифровой прорыв**")

    st.divider()

    st.write("""
    ## 📋 О приложении

    Этот инструмент предназначен для автоматизированного анализа, классификации и обработки инцидентов в сфере 
    жилищно-коммунального хозяйства (ЖКХ) и муниципальных услуг. Приложение использует искусственный интеллект 
    для ускорения обработки жалоб граждан и повышения качества обслуживания.

    ## 🚀 Основные функции

    Приложение состоит из трёх взаимосвязанных модулей:
    """)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        ### 📊 Аналитик
        **Анализ и отчётность**
        
        - Загрузка и обработка данных об инцидентах
        - Автоматический расчёт критичности проблем
        - Генерация рейтингов муниципалитетов
        - Визуализация распределения проблем по регионам
        - Экспорт отчётов в форматах TXT и XLSX
        """)

    with col2:
        st.markdown("""
        ### 🤖 Классификатор
        **Многоэтапная LLM-классификация**
        
        - **Этап 1**: определение is_problem (проблема/не проблема)
        - **Этап 2**: классификация по темам
        - **Этап 3**: маршрутизация в нужный отдел
        - Пакетная обработка с прогресс-баром
        - Экспорт результатов в CSV
        """)

    with col3:
        st.markdown("""
        ### ✍️ Генератор
        **Автоматизированная генерация ответов**
        
        - Генерация проектов ответов на жалобы
        - Учёт контекста и категории инцидента
        - Очистка текстов от спама и артефактов
        - Сохранение результатов для редактирования
        - Экспорт в CSV для дальнейшей работы
        """)

    st.divider()

    st.write("""
    ## 🔄 Рабочий процесс

    1. **Импорт данных** → Загрузите файл с инцидентами в формате .xlsx
    2. **Анализ** → Используйте страницу "Аналитик" для первичного анализа и оценки масштаба проблемы
    3. **Классификация** → На странице "Классификатор" автоматически определите категорию и ответственный отдел
    4. **Генерация ответов** → На странице "Генератор" создайте проекты ответов гражданам
    5. **Экспорт** → Скачайте результаты для дальнейшей обработки и отправки
    """)

    st.divider()

    st.write("## 📥 Демонстрационные материалы")
    st.markdown("Скачайте готовые результаты работы алгоритма на тестовой и основной выборках.")

    def load_file_for_download(filepath):
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                return f.read()
        return None

    PATHS = {
        "test_txt": "data/reports/test_report.txt",
        "test_xlsx": "data/reports/test_tops.xlsx",
        "main_txt": "data/reports/main_report.txt",
        "main_xlsx": "data/reports/main_tops.xlsx",
    }

    col_test, col_main = st.columns(2)

    with col_test:
        st.info("### 🧪 Тестовый датасет")
        
        file_data_txt = load_file_for_download(PATHS["test_txt"])
        if file_data_txt:
            st.download_button(
                label="📄 Скачать текстовый отчет",
                data=file_data_txt,
                file_name="test_report.txt",
                mime="text/plain",
                use_container_width=True,
                key="test_txt_btn" 
            )
        else:
            st.button("📄 Текстовый отчет недоступен", disabled=True, use_container_width=True, key="test_txt_disabled")

        file_data_xlsx = load_file_for_download(PATHS["test_xlsx"])
        if file_data_xlsx:
            st.download_button(
                label="📊 Скачать таблицу Топ-регионов",
                data=file_data_xlsx,
                file_name="test_tops.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True, 
                key="test_xlsx_btn" 
            )
        else:
            st.button("📊 Таблица Топ-регионов недоступна", disabled=True, use_container_width=True, key="test_xlsx_disabled")


    with col_main:
        st.success("### 🏢 Основной датасет")
        
        main_data_txt = load_file_for_download(PATHS["main_txt"])
        if main_data_txt:
            st.download_button(
                label="📄 Скачать текстовый отчет",
                data=main_data_txt,
                file_name="main_report.txt", 
                mime="text/plain",
                use_container_width=True,
                key="main_txt_btn" 
            )
        else:
            st.button("📄 Текстовый отчет недоступен", disabled=True, use_container_width=True, key="main_txt_disabled")

        main_data_xlsx = load_file_for_download(PATHS["main_xlsx"])
        if main_data_xlsx:
            st.download_button(
                label="📊 Скачать таблицу Топ-регионов",
                data=main_data_xlsx,
                file_name="main_tops.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="main_xlsx_btn" 
            )
        else:
            st.button("📊 Таблица Топ-регионов недоступна", disabled=True, use_container_width=True, key="main_xlsx_disabled")

    st.divider()

    st.write("""
    ## 📂 Форматы файлов

    **Входные данные**: файлы Excel (.xlsx) с минимум одной колонкой:
    - `Текст инцидента` — содержание жалобы или описание проблемы

    ---

    **Начните работу:** выберите нужную страницу из меню слева ⬅️
    """)
