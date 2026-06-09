"""
pages/1_analyst.py
──────────────────
Страница аналитика. Использует единое хранилище данных из session_store.
"""

import streamlit as st
import os
import polars as pl
import plotly.express as px
import pandas as pd
import sys
from pathlib import Path

from run_fast_pipeline import run_fast_processing
from run_pipeline import run_full_slow_pipeline

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from src.core.analytics import IncidentAnalytics
from src.session_store import (
    get_raw_data, get_processed_data, set_processed_data,
    is_data_loaded, get_source_name, get_pipeline_mode,
    render_sidebar_upload,
    TEMP_UPLOAD_PATH, PROCESSED_SLOW_PATH, PROCESSED_FAST_PATH,
)

st.set_page_config(page_title="Analyst | Анализатор инцидентов", layout="wide")
st.title("📊 Система анализа инцидентов ЖКХ и муниципалитетов")

# ─── Единая боковая панель загрузки ──────────────────────────────────────────
df_loaded, src_name, pipe_mode = render_sidebar_upload()

TEMP_RAW_PATH = str(TEMP_UPLOAD_PATH)
OUTPUT_TXT_REPORT = "data/output/report.txt"
OUTPUT_XLSX_REPORT = "data/output/top_municipalities.xlsx"

st.sidebar.header("Параметры обработки")

pipeline_mode = st.sidebar.radio(
    "Выберите режим обработки:",
    ["Базовое решение (fast)", "AI-решение (slow)"],
    key="analyst_pipeline_mode",
)

execute_button = st.sidebar.button("🚀 Запустить анализ", key="analyst_run", type="primary")

# ─── Проверяем, есть ли данные в сессии ──────────────────────────────────────
raw_df = df_loaded  # используем данные из render_sidebar_upload()
processed_df = get_processed_data()

if not is_data_loaded() or raw_df is None:
    st.info("⬅️ Загрузите .xlsx файл через боковую панель")
    st.stop()

st.success(f"✅ Данные загружены: {get_source_name()}")
st.write(f"📊 Записей: {len(raw_df)}, колонок: {len(raw_df.columns)}")

# Если есть обработанные данные от классификатора — показываем статус
if processed_df is not None:
    st.info(f"📦 Результаты классификации доступны: {len(processed_df)} записей")
    st.caption("Аналитик будет использовать уже классифицированные данные")

st.divider()

# ─── Запуск обработки ────────────────────────────────────────────────────────
if execute_button:
    with st.spinner("Выполняется предобработка данных, расчет метрик и генерация отчетов..."):
        # Если есть processed_df от классификатора — используем его
        if processed_df is not None:
            df_for_analytics = processed_df
            st.info("📦 Используются данные после классификации")
        else:
            # Иначе запускаем пайплайн с нуля
            if pipeline_mode == "Базовое решение (fast)":
                run_fast_processing(input_path=TEMP_RAW_PATH, output_path=str(PROCESSED_FAST_PATH))
                df_for_analytics = pl.read_csv(str(PROCESSED_FAST_PATH))
            else:
                run_full_slow_pipeline(TEMP_RAW_PATH, str(PROCESSED_SLOW_PATH))
                df_for_analytics = pl.read_csv(str(PROCESSED_SLOW_PATH))

        # Сохраняем в сессию
        set_processed_data(df_for_analytics, get_source_name(), pipeline_mode)

        analytics = IncidentAnalytics(df_for_analytics)
        
        top_regions = analytics.build_reports(
            txt_output_path=OUTPUT_TXT_REPORT,
            xlsx_output_path=OUTPUT_XLSX_REPORT
        )
        
        st.session_state["top_municipalities"] = top_regions
        st.session_state["analyzer"] = analytics
        st.session_state["processing_done"] = True
        
        st.success("✅ Анализ успешно завершен!")

# ─── Если обработка уже была сделана ─────────────────────────────────────────
if st.session_state.get("processing_done") and st.session_state.get("analyzer"):
    analytics = st.session_state["analyzer"]

    st.subheader("Скачать результаты анализа")
    
    col1, col2 = st.columns(2)
    with col1:
        if os.path.exists(OUTPUT_TXT_REPORT):
            with open(OUTPUT_TXT_REPORT, "r", encoding="utf-8") as f:
                st.download_button(
                    label="📄 Скачать текстовый отчет (Ollama AI) .txt",
                    data=f.read(),
                    file_name="Аналитический_отчет.txt",
                    mime="text/plain"
                )
    with col2:
        if os.path.exists(OUTPUT_XLSX_REPORT):
            with open(OUTPUT_XLSX_REPORT, "rb") as f:
                st.download_button(
                    label="📊 Скачать таблицы Топ-3 / Топ-10 .xlsx",
                    data=f.read(),
                    file_name="Рейтинг_муниципалитетов.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    
    st.divider()
    
    st.subheader("Визуализация структуры проблем по муниципалитетам")
    
    selected_mun = st.selectbox(
        "Выберите муниципалитет для детализации:",
        st.session_state["top_municipalities"],
        key="analyst_mun_select"
    )
    
    if selected_mun:
        chart_df = st.session_state["analyzer"].get_region_distribution(selected_mun)

        if not chart_df.is_empty():
            pandas_chart_data = chart_df.to_pandas()

            name_col = "Teма" if "Teма" in pandas_chart_data.columns else "Тема"
            pandas_chart_data = pandas_chart_data.rename(columns={name_col: "topic"})

            pandas_chart_data["count"] = pd.to_numeric(pandas_chart_data["count"], errors="coerce").fillna(0)

            total = pandas_chart_data["count"].sum()
            if total > 0:
                pandas_chart_data["pct"] = pandas_chart_data["count"] / total

                pandas_chart_data.loc[pandas_chart_data["pct"] < 0.02, "topic"] = "Другое"

                grouped = (
                    pandas_chart_data
                    .groupby("topic", as_index=False)["count"]
                    .sum()
                )

                fig = px.pie(
                    grouped,
                    values="count",
                    names="topic",
                    title=f"Соотношение типов проблем в: {selected_mun}",
                    hole=0.3,
                )
                fig.update_traces(
                    textinfo="percent",
                    textposition="inside",
                    showlegend=True
                )
                fig.update_layout(margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("В выбранном регионе суммарное количество инцидентов равно нулю.")
        else:
            st.info("В выбранном регионе отсутствуют зарегистрированные инциденты.")

    st.subheader("📊 Топ-10 муниципалитетов по суммарной критичности")
    
    top_regions_df = st.session_state["analyzer"].get_top_regions(limit=10)
    if not top_regions_df.is_empty():
        top_regions_pandas = top_regions_df.to_pandas()
        
        fig_top = px.bar(
            top_regions_pandas.sort_values("Суммы баллов", ascending=True),
            x="Суммы баллов",
            y="Муниципалитет",
            orientation="h",
            title="Рейтинг муниципалитетов по критичности проблем",
            labels={"Суммы баллов": "Критичность (баллы)", "Муниципалитет": ""},
            color="Суммы баллов",
            color_continuous_scale="Viridis"
        )
        fig_top.update_layout(
            height=400,
            margin=dict(l=150, r=20, t=40, b=20),
            coloraxis_colorbar=dict(title="Баллы")
        )
        st.plotly_chart(fig_top, use_container_width=True)
    
    st.divider()

elif is_data_loaded():
    st.info("📁 Данные загружены. Нажмите **«Запустить анализ»** в боковой панели для обработки.")
    if processed_df is not None:
        st.dataframe(processed_df.to_pandas().head(10), use_container_width=True)
