"""
pages/4_map.py
──────────────
Интерактивная карта Омска с визуализацией инцидентов.
Инциденты отображаются в виде вспышек (кружков) по реальным координатам улиц.
Размер и цвет кружка зависят от severity (1-5).
"""

import os
import sys
from pathlib import Path

import streamlit as st
import polars as pl
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.map_utils import (
    load_streets_mapping,
    build_incident_map,
    get_district_stats,
    DISTRICT_COLORS,
)

st.set_page_config(page_title="Карта | Анализатор инцидентов", layout="wide")
st.title("🗺️ Интерактивная карта инцидентов Омска")
st.markdown(
    "Визуализация происшествий по реальным координатам улиц. "
    "**Размер кружка** → уровень опасности (1–5). "
    "**Цвет** → от зелёного (1) до красного (5). "
    "Особо опасные (4–5) выделены гало."
)

# ─── Пути к данным ───────────────────────────────────────────────────────────
PROCESSED_CSV_SLOW = "data/processed/тестовый_файл_slow.csv"
PROCESSED_CSV_FAST = "data/processed/основной_файл_slow.csv"

# ─── Состояние сессии ────────────────────────────────────────────────────────
if "map_data_loaded" not in st.session_state:
    st.session_state["map_data_loaded"] = False
if "map_df" not in st.session_state:
    st.session_state["map_df"] = None

# ─── Боковая панель ──────────────────────────────────────────────────────────
st.sidebar.header("⚙️ Параметры карты")

st.sidebar.subheader("📂 Источник данных")
data_source = st.sidebar.radio(
    "Выберите данные:",
    ["AI-решение (slow)", "Базовое решение (fast)", "Загрузить свой CSV"],
)

uploaded_file = None
if data_source == "Загрузить свой CSV":
    uploaded_file = st.sidebar.file_uploader(
        "Загрузите CSV с обработанными инцидентами",
        type=["csv"],
        key="map_upload",
    )

# Фильтры
st.sidebar.subheader("🔍 Фильтры")

district_list = list(DISTRICT_COLORS.keys())
selected_district = st.sidebar.selectbox(
    "Район:",
    ["Все районы"] + district_list,
    key="map_district_filter",
)

min_severity = st.sidebar.slider(
    "Минимальный уровень опасности:",
    min_value=0, max_value=5, value=1,
    key="map_severity_filter",
    help="Показывать инциденты с опасностью от выбранного уровня",
)

load_button = st.sidebar.button("🔄 Загрузить и построить карту", key="map_load_btn")

# ─── Загрузка данных ─────────────────────────────────────────────────────────
streets_mapping = load_streets_mapping()

if load_button:
    with st.spinner("Загрузка данных..."):
        df = None
        if data_source == "AI-решение (slow)":
            if os.path.exists(PROCESSED_CSV_SLOW):
                df = pl.read_csv(PROCESSED_CSV_SLOW)
            else:
                st.error(f"❌ Файл не найден: {PROCESSED_CSV_SLOW}")
        elif data_source == "Базовое решение (fast)":
            if os.path.exists(PROCESSED_CSV_FAST):
                df = pl.read_csv(PROCESSED_CSV_FAST)
            else:
                st.error(f"❌ Файл не найден: {PROCESSED_CSV_FAST}")
        elif data_source == "Загрузить свой CSV" and uploaded_file is not None:
            df = pl.read_csv(uploaded_file)

        if df is not None:
            st.session_state["map_df"] = df
            st.session_state["map_data_loaded"] = True
            st.sidebar.success(f"✅ Загружено {len(df)} записей")
        else:
            st.sidebar.warning("⚠️ Не удалось загрузить данные")

# ─── Отображение карты ───────────────────────────────────────────────────────
if st.session_state["map_data_loaded"] and st.session_state["map_df"] is not None:
    df = st.session_state["map_df"]
    district_filter = selected_district if selected_district != "Все районы" else None

    with st.spinner("Построение карты..."):
        try:
            incident_map = build_incident_map(
                incidents_df=df,
                streets_mapping=streets_mapping,
                district_filter=district_filter,
                min_severity=min_severity,
            )
            map_html = incident_map._repr_html_()
            st.components.v1.html(map_html, height=700, width=None)
        except Exception as e:
            st.error(f"Ошибка при построении карты: {e}")
            st.exception(e)

    # ─── Статистика ──────────────────────────────────────────────────────
    st.divider()
    st.subheader("📊 Статистика по районам")

    stats = get_district_stats(df, streets_mapping)
    cols = st.columns(len(stats))
    for idx, (district, info) in enumerate(stats.items()):
        with cols[idx]:
            color = info["color"]
            st.markdown(
                f"""
                <div style="
                    background: {color}15; border-radius: 10px; padding: 12px;
                    border-left: 4px solid {color}; text-align: center;
                ">
                    <h4 style="margin:0; color:{color};">{district}</h4>
                    <div style="font-size:28px; font-weight:bold; margin:8px 0;">{info["count"]}</div>
                    <div style="font-size:13px; color:#666;">
                        инцидентов<br>
                        Средняя опасность: <b>{info["avg_severity"]}</b>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ─── Детализация ─────────────────────────────────────────────────────
    st.divider()
    st.subheader("🔎 Детализация по районам")
    expand_district = st.selectbox(
        "Выберите район:", [""] + district_list, key="map_detail_district"
    )
    if expand_district and expand_district in stats:
        info = stats[expand_district]
        c1, c2 = st.columns(2)
        c1.metric("Всего инцидентов", info["count"])
        c2.metric("Средняя опасность", info["avg_severity"])
        if info["topics"]:
            st.markdown("**Топ проблем:**")
            topics_df = pd.DataFrame(
                list(info["topics"].items()), columns=["Тема", "Количество"]
            )
            topics_df["%"] = (topics_df["Количество"] / topics_df["Количество"].sum() * 100).round(1)
            st.dataframe(topics_df, use_container_width=True, hide_index=True)

    with st.expander("📋 Показать сырые данные"):
        st.dataframe(df.to_pandas(), use_container_width=True)

else:
    st.info("⬅️ Выберите источник данных в боковой панели и нажмите **«Загрузить и построить карту»**")

    # Превью пустой карты с районами
    st.markdown("---")
    st.markdown("### 👀 Предпросмотр: районы Омска")
    empty_map = build_incident_map(
        incidents_df=pl.DataFrame({"Улица": [], "Тема": [], "severity": [], "is_problem": []}),
        streets_mapping=streets_mapping,
    )
    st.components.v1.html(empty_map._repr_html_(), height=500, width=None)
    st.caption("💡 *После загрузки данных на карте появятся инциденты с реальными координатами улиц.*")