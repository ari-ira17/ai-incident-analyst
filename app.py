import streamlit as st
import os

from src.workspace import render_workspace_panel, init_workspace

# Настройка страницы
st.set_page_config(page_title="AI-Аналитик инцидентов | Платформа", layout="wide", initial_sidebar_state="expanded")

# Внедрение Enterprise CSS-стиля (шрифт Inter, строгие компоненты)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Применение шрифта Inter ко всему приложению */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }

    /* Цветовые переменные для адаптации светлой/темной темы */
    :root {
    --ent-border: rgba(128, 128, 128, 0.25);
    --ent-card-bg: var(--secondary-background-color);
    --ent-text-muted: gray;

    --ent-accent: #0f62fe;

    --accent-blue: #0f62fe;
    --accent-green: #24a148;
    --accent-orange: #f59e0b;
    --accent-purple: #8b5cf6;

    --accent-blue-bg: rgba(15,98,254,.08);
    --accent-green-bg: rgba(36,161,72,.08);
    --accent-orange-bg: rgba(245,158,11,.08);
    --accent-purple-bg: rgba(139,92,246,.08);
    }

    /* Enterprise Заголовок */
    .enterprise-header {
        margin-top: 0;
        margin-bottom: 0.2rem;
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    .enterprise-subtitle {
        font-size: 1.1rem;
        color: var(--ent-text-muted);
        margin-bottom: 2rem;
        padding-bottom: 1rem;
        border-bottom: 1px solid var(--ent-border);
    }
    .hero-badge {
        display:inline-block;
        padding:5px 12px;
        background:var(--accent-blue-bg);
        color:var(--accent-blue);
        border-radius:999px;
        font-size:.75rem;
        font-weight:700;
        letter-spacing:.08em;
        margin-bottom:.8rem;
    }
    .hero-title-wrap {
        position: relative;
        padding-left: 18px;
        display: flex;
        align-items: center;
        margin-bottom: 0.5rem;
    }
    .hero-title-wrap::before {
        content: "";
        position: absolute;
        left: 0;
        width: 5px;
        height: 80%;
        border-radius: 10px;
        background: #0f62fe;
    }
    .enterprise-header {
        margin: 0;
        font-size: 2.4rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        line-height: 1.1;
    }
    /* Карточки модулей */
    .ent-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
        align-items: stretch; /* Форсирует одинаковую высоту всех элементов в строке */
    }
    .ent-card {
        position: relative;
        background-color: var(--ent-card-bg);
        border: 2px solid rgba(15,98,254,.08);
        border-radius: 12px;
        padding: 1.6rem;
        box-shadow:
            0 4px 10px rgba(0,0,0,.03),
            0 1px 2px rgba(0,0,0,.04);
        transition: all .25s ease;
        overflow: hidden;
    }
    .ent-card:hover {
        transform: translateY(-4px);
        border-color: rgba(15,98,254,.35);
        box-shadow:
            0 18px 32px rgba(0,0,0,.08),
            0 6px 12px rgba(15,98,254,.06);
    }
    .ent-card::before{
        content:"";
        position:absolute;
        top:0;
        left:0;
        width:100%;
        height:4px;
    }

    .ent-grid .ent-card:nth-child(1)::before{
        background:linear-gradient(
            90deg,
            var(--accent-blue),
            #4589ff
        );
    }

    .ent-grid .ent-card:nth-child(2)::before{
        background:linear-gradient(
            90deg,
            var(--accent-purple),
            #a78bfa
        );
    }

    .ent-grid .ent-card:nth-child(3)::before{
        background:linear-gradient(
            90deg,
            var(--accent-green),
            #34d399
        );
    }  
    .ent-card-header {
        font-size: 1.2rem;
        font-weight: 700;
        margin-bottom: .4rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .ent-card-header::before {
        content: "";
        display: inline-block;
        width: 4px;
        height: 16px;
        background-color: var(--ent-accent);
        border-radius: 2px;
    }
    .ent-card-meta {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--ent-text-muted);
        margin-bottom: 1rem;
        font-weight: 500;
    }
    .ent-card-body {
        font-size: 0.9rem;
        line-height: 1.5;
        color: var(--text-color);
        padding-left: 1.2rem;
    }
    .ent-card-body li {
        margin-bottom: 0.5rem;
    }

    /* Горизонтальный Workflow */
    .workflow-container {
        display: flex;
        gap: 1rem;
        margin-bottom: 2rem;
        flex-wrap: wrap;
    }
    .workflow-step-hz {
        flex: 1;
        min-width: 180px;
        background-color: var(--ent-card-bg);
        border: 1px solid var(--ent-border);
        border-radius: 8px;
        padding: 1.25rem 1rem;
        position: relative;
        transition: all .2s ease;
    }
    .workflow-step-hz:hover{
        transform: translateY(-2px);
        border-color: var(--accent-blue);
    }
    .step-num-hz {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--ent-accent);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }
    .step-title-hz {
        font-size: 0.95rem;
        font-weight: 600;
        margin-bottom: 0.25rem;
    }
    .step-desc-hz {
        font-size: 0.85rem;
        color: var(--ent-text-muted);
        line-height: 1.4;
    }

    /* Заголовки секций */
    .section-title {
        font-size: 1.25rem;
        font-weight: 600;
        margin-top: 2rem;
        margin-bottom: 1.25rem;
        letter-spacing: -0.01em;
    }
            
    .kpi-grid {
        display:grid;
        grid-template-columns:
            repeat(4, 1fr);
        gap:1rem;
        margin-bottom:2rem;
    }

    .kpi-card {
        background:var(--ent-card-bg);
        border:1px solid rgba(15,98,254,.10);
        border-radius:12px;
        padding:1rem 1.2rem;
        transition:all .2s ease;
    }

    .kpi-card:hover{
        transform:translateY(-2px);
        box-shadow:
            0 10px 24px rgba(0,0,0,.06);
    }

    .kpi-label{
        font-size:.75rem;
        text-transform:uppercase;
        letter-spacing:.05em;
        color:gray;
        margin-bottom:.5rem;
    }

    .kpi-value{
        font-size:1.8rem;
        font-weight:700;
    }

    .kpi-desc{
        margin-top:.4rem;
        font-size:.8rem;
        color:gray;
    }
</style>
""", unsafe_allow_html=True)

init_workspace()

left_col, right_col = st.columns([3, 1], gap="large")

with right_col:
    render_workspace_panel()

with left_col:
    # Строгий заголовок
    st.markdown("""
<div class="hero-badge">
    PROBLEMHUNTER
</div>

<div class="hero-title-wrap">
    <h1 class="enterprise-header">
        AI-Аналитик инцидентов
    </h1>
</div>

<div class='enterprise-subtitle'>
    Система автоматизированной классификации и маршрутизации обращений граждан
</div>
""", unsafe_allow_html=True)

    # Дашборд KPI
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric(label="Пропускная способность", value="400k+", delta="строк/пакет", delta_color="off")
    with kpi2:
        st.metric(label="Точность маршрутизации", value="94.8%", delta="на тестовой выборке", delta_color="normal")
    with kpi3:
        st.metric(label="Модель обработки", value="LLM", delta="Локальный / API контур", delta_color="off")
    with kpi4:
        st.metric(label="Анализ тональности", value="Включен", delta="Оценка критичности", delta_color="normal")

    st.markdown("<h3 class='section-title'>Архитектура решения</h3>", unsafe_allow_html=True)

    # Выравнивание карточек через нативный CSS Grid (без st.columns)
    st.markdown("""
    <div class="ent-grid">
        <div class="ent-card">
            <div class="ent-card-header">Аналитик</div>
            <div class="ent-card-meta">Сводка и метрики</div>
            <ul class="ent-card-body">
                <li>Загрузка и нормализация данных</li>
                <li>Расчет индексов критичности (Severity)</li>
                <li>Формирование рейтингов муниципалитетов</li>
                <li>Агрегация статистики по регионам</li>
                <li>Экспорт матричных отчетов (XLSX)</li>
            </ul>
        </div>
        <div class="ent-card">
            <div class="ent-card-header">Классификатор</div>
            <div class="ent-card-meta">Пайплайн разметки</div>
            <ul class="ent-card-body">
                <li>Бинарная фильтрация (проблема / не проблема)</li>
                <li>Многоклассовая тематическая рубрикация</li>
                <li>Определение целевого ведомства</li>
                <li>Асинхронная пакетная обработка</li>
                <li>Логирование результатов в CSV</li>
            </ul>
        </div>
        <div class="ent-card">
            <div class="ent-card-header">Генератор</div>
            <div class="ent-card-meta">Синтез ответов</div>
            <ul class="ent-card-body">
                <li>Формирование проектов официальных ответов</li>
                <li>Применение нормативно-правового контекста</li>
                <li>Очистка от нерелевантной информации</li>
                <li>Система сохранения черновиков</li>
                <li>Интеграционный экспорт данных</li>
            </ul>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<h3 class='section-title'>Регламент обработки данных</h3>", unsafe_allow_html=True)
    
    # Горизонтальный Workflow
    st.markdown("""
    <div class="workflow-container">
        <div class="workflow-step-hz">
            <div class="step-num-hz">Этап 01</div>
            <div class="step-title-hz">Импорт данных</div>
            <div class="step-desc-hz">Загрузка реестра в формате XLSX через системный Workspace.</div>
        </div>
        <div class="workflow-step-hz">
            <div class="step-num-hz">Этап 02</div>
            <div class="step-title-hz">Мониторинг</div>
            <div class="step-desc-hz">Оценка масштаба аномалий в модуле «Аналитик».</div>
        </div>
        <div class="workflow-step-hz">
            <div class="step-num-hz">Этап 03</div>
            <div class="step-title-hz">Маршрутизация</div>
            <div class="step-desc-hz">Запуск ML-пайплайна определения ответственных инстанций.</div>
        </div>
        <div class="workflow-step-hz">
            <div class="step-num-hz">Этап 04</div>
            <div class="step-title-hz">Документооборот</div>
            <div class="step-desc-hz">Синтез шаблонов ответов в модуле «Генератор».</div>
        </div>
        <div class="workflow-step-hz">
            <div class="step-num-hz">Этап 05</div>
            <div class="step-title-hz">Выгрузка</div>
            <div class="step-desc-hz">Экспорт управленческих отчетов для руководства.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Блок "Отчетный центр"
    st.markdown("<h3 class='section-title'>Отчетный центр</h3>", unsafe_allow_html=True)
    st.write("Доступны прекалькулированные аналитические сводки и Топ-рейтинги для ознакомления с форматом вывода.")

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
        with st.container(border=True):
            st.markdown("<div style='font-weight:600; font-size:1.05rem; margin-bottom:0.2rem;'>Тестовая выборка</div>", unsafe_allow_html=True)
            st.markdown("<div style='font-size:0.85rem; color:gray; margin-bottom:1rem;'>Срез данных для валидации</div>", unsafe_allow_html=True)
            
            file_data_txt = load_file_for_download(PATHS["test_txt"])
            if file_data_txt:
                st.download_button(
                    label="Скачать аналитическую справку (TXT)",
                    data=file_data_txt,
                    file_name="test_report.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key="test_txt_btn" 
                )
            else:
                st.button("Аналитическая справка недоступна", disabled=True, use_container_width=True, key="test_txt_disabled")

            file_data_xlsx = load_file_for_download(PATHS["test_xlsx"])
            if file_data_xlsx:
                st.download_button(
                    label="Скачать матрицу инцидентов (XLSX)",
                    data=file_data_xlsx,
                    file_name="test_tops.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True, 
                    key="test_xlsx_btn",
                    type="primary"
                )
            else:
                st.button("Матрица инцидентов недоступна", disabled=True, use_container_width=True, key="test_xlsx_disabled")


    with col_main:
        with st.container(border=True):
            st.markdown("<div style='font-weight:600; font-size:1.05rem; margin-bottom:0.2rem;'>Генеральная совокупность (400k)</div>", unsafe_allow_html=True)
            st.markdown("<div style='font-size:0.85rem; color:gray; margin-bottom:1rem;'>Итоговый управленческий отчет</div>", unsafe_allow_html=True)
            
            main_data_txt = load_file_for_download(PATHS["main_txt"])
            if main_data_txt:
                st.download_button(
                    label="Скачать аналитическую справку (TXT)",
                    data=main_data_txt,
                    file_name="main_report.txt", 
                    mime="text/plain",
                    use_container_width=True,
                    key="main_txt_btn" 
                )
            else:
                st.button("Аналитическая справка недоступна", disabled=True, use_container_width=True, key="main_txt_disabled")

            main_data_xlsx = load_file_for_download(PATHS["main_xlsx"])
            if main_data_xlsx:
                st.download_button(
                    label="Скачать матрицу инцидентов (XLSX)",
                    data=main_data_xlsx,
                    file_name="main_tops.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="main_xlsx_btn",
                    type="primary"
                )
            else:
                st.button("Матрица инцидентов недоступна", disabled=True, use_container_width=True, key="main_xlsx_disabled")

    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("""
        <div style="padding: 1rem; border-left: 4px solid var(--ent-accent); background-color: var(--ent-card-bg); border-radius: 0 4px 4px 0; font-size: 0.9rem;">
            <strong>Системное уведомление:</strong> Для инициализации работы выберите необходимый модуль в навигационной панели. Допустимый формат входных данных — Microsoft Excel (.xlsx) при обязательном наличии столбца «Текст инцидента».
        </div>
    """, unsafe_allow_html=True)