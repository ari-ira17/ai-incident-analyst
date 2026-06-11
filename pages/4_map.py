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

st.markdown("""
<style>

/* =========================
   MAP PAGE HEADER (shared style)
========================= */

.page-header{
    margin-bottom:2rem;
}

.page-badge{
    display:inline-block;
    padding:6px 12px;
    border-radius:999px;
    background:rgba(15,98,254,.08);
    color:#0f62fe;
    font-size:.75rem;
    font-weight:700;
    letter-spacing:.08em;
    margin-bottom:.8rem;
}

.title-row{
    display:flex;
    align-items:center;
    gap:14px;
}

.title-bar{
    width:5px;
    height:44px;
    background:#0f62fe;
    border-radius:3px;
    flex-shrink:0;
}

.page-title{
    font-size:2.2rem;
    font-weight:700;
    margin:0;
    line-height:1.1;
}

.page-subtitle{
    margin-top:.8rem;
    color:var(--text-color);
    opacity:0.75;
    font-size:1rem;
    padding-bottom:1rem;
    border-bottom:1px solid rgba(120,120,120,.2);
}

/* =========================
   INFO BLOCK (map description)
========================= */

.map-info{
    padding:1rem 1.2rem;
    border-radius:12px;
    border:1px solid rgba(15,98,254,.18);
    border-left:5px solid #0f62fe;
    background:var(--secondary-background-color);
    margin: 1rem 0 1.5rem 0;
    font-size:0.95rem;
    line-height:1.5;
}

/* =========================
   SIDEBAR STYLE (optional polish)
========================= */

section[data-testid="stSidebar"]{
    border-right:1px solid rgba(120,120,120,.2);
}

</style>
""", unsafe_allow_html=True)


st.set_page_config(page_title="Карта | Анализатор инцидентов", layout="wide")

st.markdown("""
<div class="page-header">

<div class="page-badge">
MAP MODULE
</div>

<div class="title-row">
    <div class="title-bar"></div>
    <h1 class="page-title">
        Интерактивная карта инцидентов Омска
    </h1>
</div>

<div class="page-subtitle">
Визуализация происшествий по реальным координатам улиц
</div>

</div>
""", unsafe_allow_html=True)



init_workspace()


left_col, right_col = st.columns([3, 1])

with right_col:
    render_workspace_panel(active_page="map")

with left_col:
    st.markdown("""
    <div class="map-info">
    <b>Что отображается на карте:</b><br>
    • Размер кружка → уровень опасности (1–5)<br>
    • Цвет → от зелёного (низкий риск) до красного (высокий риск)<br>
    • Особо опасные инциденты (4–5) выделяются визуально усиленным маркером
    </div>
    """, unsafe_allow_html=True)

 
    streets_mapping = load_streets_mapping()
    ws = get_workspace()
    analyzed_file_path = ws.get("analyzed_file")

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

        st.markdown("---")
        st.markdown("### 👀 Предпросмотр: районы Омска")
        empty_map = build_incident_map(
            incidents_df=pl.DataFrame({"Улица": [], "Тема": [], "severity": [], "is_problem": []}),
            streets_mapping=streets_mapping,
        )
        st.components.v1.html(empty_map._repr_html_(), height=500, width=None)
        st.caption("💡 *После выбора файла на карте появятся инциденты с реальными координатами улиц.*")
