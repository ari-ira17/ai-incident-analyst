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

from src.workspace import render_workspace_panel, init_workspace, get_workspace, set_workspace_file, FileManager

st.set_page_config(page_title="Analyst | Анализатор инцидентов", layout="wide")
st.title("📊 Система анализа инцидентов ЖКХ и муниципалитетов")

# ============ ИНИЦИАЛИЗАЦИЯ WORKSPACE ============
init_workspace()

# Основной контент (слева) и workspace (справа)
left_col, right_col = st.columns([3, 1])

with right_col:
    render_workspace_panel(active_page="analyst")

with left_col:
    fm = FileManager()

    # ============ ПАРАМЕТРЫ ОБРАБОТКИ ============
    st.sidebar.header("Параметры обработки")

    pipeline_mode = st.sidebar.radio(
        "Выберите режим обработки:", 
        ["Базовое решение (fast)", "AI-решение (slow)"]
    )

    execute_button = st.sidebar.button("Запустить анализ", key="analyst_run")

    # ============ ОСНОВНОЙ КОНТЕНТ ============
    ws = get_workspace()
    classified_file_path = ws.get("classified_file")

    if classified_file_path is None:
        st.info("⬅️ Выберите классифицированный файл в правой панели Workspace (папка «Классифицированные»).")
    else:
        st.success(f"✅ Выбран файл: `{os.path.basename(classified_file_path)}`")

        if execute_button:
            with st.spinner("Выполняется предобработка данных, расчет метрик и генерация отчетов..."):
                base_name = os.path.splitext(os.path.basename(classified_file_path))[0]
                analyzed_filename = f"{base_name}_analyzed.xlsx"
                analyzed_path = fm.get_output_path("analyzed", analyzed_filename)
                
                report_txt_filename = f"{base_name}_report.txt"
                report_xlsx_filename = f"{base_name}_report.xlsx"
                report_txt_path = fm.get_output_path("reports", report_txt_filename)
                report_xlsx_path = fm.get_output_path("reports", report_xlsx_filename)

                if pipeline_mode == "Базовое решение (fast)":
                    run_fast_processing(input_path=classified_file_path, output_path=analyzed_path)
                else:
                    run_full_slow_pipeline(classified_file_path, analyzed_path)
                    
                df_processed = pl.read_excel(analyzed_path, engine="calamine")
                analytics = IncidentAnalytics(df_processed)
                
                top_regions = analytics.build_reports(
                    txt_output_path=report_txt_path,
                    xlsx_output_path=report_xlsx_path
                )
                
                set_workspace_file("analyzed", analyzed_path)
                
                st.session_state["top_municipalities"] = top_regions
                st.session_state["analyzer"] = analytics
                st.session_state["processing_done"] = True
                
                st.success("Анализ успешно завершен!")

        if st.session_state.get("processing_done"):
            st.subheader("Скачать результаты анализа")
            
            ws = get_workspace()
            classified_path = ws.get("classified_file", "")
            base_name = os.path.splitext(os.path.basename(classified_path))[0] if classified_path else "report"
            
            report_txt_path = fm.get_output_path("reports", f"{base_name}_report.txt")
            report_xlsx_path = fm.get_output_path("reports", f"{base_name}_report.xlsx")
            analyzed_path = ws.get("analyzed_file", "")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if os.path.exists(report_txt_path):
                    with open(report_txt_path, "r", encoding="utf-8") as f:
                        st.download_button(
                            label="Скачать текстовый отчет (Ollama AI) .txt",
                            data=f.read(),
                            file_name=f"{base_name}_report.txt",
                            mime="text/plain"
                        )
            with col2:
                if os.path.exists(report_xlsx_path):
                    with open(report_xlsx_path, "rb") as f:
                        st.download_button(
                            label="Скачать таблицы Топ-3 / Топ-10 .xlsx",
                            data=f.read(),
                            file_name=f"{base_name}_report.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
            with col3:
                if analyzed_path and os.path.exists(analyzed_path):
                    with open(analyzed_path, "rb") as f:
                        st.download_button(
                            label="Скачать обработанные данные .xlsx",
                            data=f.read(),
                            file_name=os.path.basename(analyzed_path),
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
