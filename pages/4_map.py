"""
pages/4_map.py
──────────────
Интерактивная карта Омска с визуализацией инцидентов.
Инциденты отображаются в виде кружков по реальным координатам улиц.
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

from src.map_utils.map_utils import (
    load_streets_mapping,
    build_incident_map,
    get_district_stats,
    DISTRICT_COLORS,
)
from src.workspace import render_workspace_panel, init_workspace, get_workspace

st.set_page_config(page_title="Карта | Анализатор инцидентов", layout="wide")
st.title("🗺️ Интерактивная карта инцидентов Омска")

# ─── ИНИЦИАЛИЗАЦИЯ WORKSPACE ──────────────────────────────────────────
init_workspace()

# Основной контент (слева) и workspace (справа)
left_col, right_col = st.columns([3, 1])

with right_col:
    render_workspace_panel(active_page="map")

with left_col:
    st.markdown(
        "Визуализация происшествий по реальным координатам улиц. "
        "**Размер кружка** → уровень опасности (1–5). "
        "**Цвет** → от зелёного (1) до красного (5). "
        "Особо опасные (4–5) выделены гало."
    )

    # ─── Загрузка данных через workspace ──────────────────────────────────
    streets_mapping = load_streets_mapping()
    ws = get_workspace()
    analyzed_file_path = ws.get("analyzed_file")

    # ─── Боковая панель ──────────────────────────────────────────────────
    st.sidebar.header("⚙️ Параметры карты")

    district_list = list(DISTRICT_COLORS.keys())
    selected_district = st.sidebar.selectbox(
        "🏘️ Район:",
        ["Все районы"] + district_list,
        key="map_district_filter",
    )

    min_severity = st.sidebar.slider(
        "🔥 Мин. уровень опасности:",
        min_value=0, max_value=5, value=1,
        key="map_severity_filter",
        help="Показывать инциденты с опасностью от выбранного уровня",
    )

    # ─── Отображение карты ───────────────────────────────────────────────
    if analyzed_file_path and os.path.exists(analyzed_file_path):
        try:
            df = pl.read_excel(analyzed_file_path, engine="calamine")
        except Exception:
            df = pl.read_excel(analyzed_file_path)

        if df is not None and len(df) > 0:
            st.success(f"✅ Данные загружены: `{os.path.basename(analyzed_file_path)}` | Записей: {len(df)}")

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

            # ─── Статистика ──────────────────────────────────────────────────
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

            # ─── Детализация ─────────────────────────────────────────────────
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
            st.warning("⚠️ Данные загружены, но пусты.")
    else:
        st.info("⬅️ Выберите обработанный файл в правой панели Workspace (папка «Обработанные (с severity)»).")

        # Превью пустой карты с районами
        st.markdown("---")
        st.markdown("### 👀 Предпросмотр: районы Омска")
        empty_map = build_incident_map(
            incidents_df=pl.DataFrame({"Улица": [], "Тема": [], "severity": [], "is_problem": []}),
            streets_mapping=streets_mapping,
        )
        st.components.v1.html(empty_map._repr_html_(), height=500, width=None)
        st.caption("💡 *После выбора файла на карте появятся инциденты с реальными координатами улиц.*")