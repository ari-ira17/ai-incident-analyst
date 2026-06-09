"""
src/map_utils/session_store.py
──────────────────────────────
Управление session_state для страницы карты.
"""

import os
import streamlit as st
import polars as pl
from pathlib import Path

# __file__ = src/map_utils/session_store.py -> parent = src/map_utils -> parent = src -> parent = project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Ключи для session_state
_STATE_KEY = "map_processed_data"
_SOURCE_KEY = "map_source_name"
_LOADED_KEY = "map_data_loaded"


def get_processed_data() -> pl.DataFrame | None:
    """Возвращает обработанные данные из session_state."""
    return st.session_state.get(_STATE_KEY)


def is_data_loaded() -> bool:
    """Проверяет, загружены ли данные."""
    return st.session_state.get(_LOADED_KEY, False)


def get_source_name() -> str:
    """Возвращает имя источника данных."""
    return st.session_state.get(_SOURCE_KEY, "Неизвестно")


def render_sidebar_upload() -> tuple[pl.DataFrame | None, str, str]:
    """
    Рендерит боковую панель загрузки файла.
    Возвращает (df, source_name, pipeline_mode).
    """
    st.sidebar.header("📂 Загрузка данных для карты")

    uploaded_file = st.sidebar.file_uploader(
        "Загрузите .xlsx с обработанными данными",
        type=["xlsx"],
        key="map_file_uploader",
    )

    if uploaded_file is not None:
        try:
            df = pl.read_excel(uploaded_file, engine="calamine")
            st.session_state[_STATE_KEY] = df
            st.session_state[_SOURCE_KEY] = uploaded_file.name
            st.session_state[_LOADED_KEY] = True
            st.sidebar.success(f"✅ Загружено: {uploaded_file.name} ({len(df)} записей)")
            return df, uploaded_file.name, "upload"
        except Exception as e:
            st.sidebar.error(f"❌ Ошибка загрузки: {e}")
            return None, "", ""

    # Если данных нет, но есть processed файл от аналитика
    processed_path = os.path.join(PROJECT_ROOT, "data/processed/тестовый_файл_slow.xlsx")
    if os.path.exists(processed_path):
        if st.sidebar.button("📂 Использовать последние обработанные данные", key="map_use_processed"):
            try:
                df = pl.read_excel(processed_path, engine="calamine")
                st.session_state[_STATE_KEY] = df
                st.session_state[_SOURCE_KEY] = "тестовый_файл_slow.xlsx"
                st.session_state[_LOADED_KEY] = True
                st.sidebar.success(f"✅ Загружено: тестовый_файл_slow.xlsx ({len(df)} записей)")
                return df, "тестовый_файл_slow.xlsx", "processed"
            except Exception as e:
                st.sidebar.error(f"❌ Ошибка: {e}")

    return None, "", ""