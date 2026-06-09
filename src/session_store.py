"""
session_store.py
────────────────
Единое хранилище данных сессии для всех страниц Streamlit.
Позволяет загрузить файл один раз и использовать на всех вкладках.
"""

import os
from pathlib import Path
from typing import Optional

import streamlit as st
import polars as pl


# ─── Константы ───────────────────────────────────────────────────────────────
SESSION_KEY = "app_session_data"

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
OUTPUT_DIR = Path("data/output")

TEMP_UPLOAD_PATH = RAW_DIR / "temp_uploaded.xlsx"
PROCESSED_SLOW_PATH = PROCESSED_DIR / "тестовый_файл_slow.xlsx"
PROCESSED_FAST_PATH = PROCESSED_DIR / "основной_файл_slow.xlsx"

TEST_FILE_FAST = RAW_DIR / "тестовый файл.xlsx"
TEST_FILE_SLOW = RAW_DIR / "test_40.xlsx"


def init_session():
    """Инициализирует ключи сессии при первом запуске"""
    if SESSION_KEY not in st.session_state:
        st.session_state[SESSION_KEY] = {
            "raw_df": None,          # polars DataFrame сырых данных
            "processed_df": None,    # polars DataFrame обработанных данных
            "source_name": "",       # имя источника (файла)
            "pipeline_mode": "",     # fast / slow
            "is_loaded": False,
        }


def get_session() -> dict:
    """Возвращает словарь данных сессии"""
    init_session()
    return st.session_state[SESSION_KEY]


def set_processed_data(df: pl.DataFrame, source_name: str, mode: str):
    """Сохраняет обработанные данные в сессию"""
    init_session()
    st.session_state[SESSION_KEY]["processed_df"] = df
    st.session_state[SESSION_KEY]["source_name"] = source_name
    st.session_state[SESSION_KEY]["pipeline_mode"] = mode
    st.session_state[SESSION_KEY]["is_loaded"] = True


def set_raw_data(df: pl.DataFrame, source_name: str):
    """Сохраняет сырые данные в сессию"""
    init_session()
    st.session_state[SESSION_KEY]["raw_df"] = df
    st.session_state[SESSION_KEY]["source_name"] = source_name
    st.session_state[SESSION_KEY]["is_loaded"] = True


def get_processed_data() -> Optional[pl.DataFrame]:
    """Возвращает обработанные данные из сессии"""
    init_session()
    return st.session_state[SESSION_KEY].get("processed_df")


def get_raw_data() -> Optional[pl.DataFrame]:
    """Возвращает сырые данные из сессии"""
    init_session()
    return st.session_state[SESSION_KEY].get("raw_df")


def is_data_loaded() -> bool:
    """Проверяет, загружены ли данные"""
    init_session()
    return st.session_state[SESSION_KEY].get("is_loaded", False)


def get_source_name() -> str:
    """Возвращает имя источника данных"""
    init_session()
    return st.session_state[SESSION_KEY].get("source_name", "")


def get_pipeline_mode() -> str:
    """Возвращает режим обработки"""
    init_session()
    return st.session_state[SESSION_KEY].get("pipeline_mode", "")


def clear_session():
    """Очищает данные сессии"""
    init_session()
    st.session_state[SESSION_KEY] = {
        "raw_df": None,
        "processed_df": None,
        "source_name": "",
        "pipeline_mode": "",
        "is_loaded": False,
    }


def load_processed_xlsx(path: Path) -> Optional[pl.DataFrame]:
    """Загружает обработанный XLSX файл через Polars"""
    if not path.exists():
        return None
    try:
        return pl.read_excel(str(path), engine="calamine")
    except Exception as e:
        st.error(f"Ошибка загрузки {path}: {e}")
        return None


def save_processed_xlsx(df: pl.DataFrame, path: Path):
    """Сохраняет DataFrame в XLSX"""
    os.makedirs(path.parent, exist_ok=True)
    df.write_excel(str(path))


def render_sidebar_upload():
    """
    Отрисовывает единую панель загрузки в боковой панели.
    Возвращает (df, source_name, pipeline_mode) или (None, "", "").
    """
    init_session()

    st.sidebar.header("📂 Данные")

    # Если данные уже загружены — показываем статус и кнопку очистки
    if is_data_loaded():
        st.sidebar.success(f"✅ Данные загружены")
        st.sidebar.info(f"📊 {get_source_name()}")
        raw = get_raw_data()
        if raw is not None:
            st.sidebar.caption(f"Записей: {len(raw)}, колонок: {len(raw.columns)}")
        if st.sidebar.button("🔄 Очистить и загрузить новые", key="global_clear"):
            clear_session()
            st.rerun()
        return get_raw_data(), get_source_name(), get_pipeline_mode()

    # Проверка тестовых файлов
    has_fast = TEST_FILE_FAST.exists()
    has_slow = TEST_FILE_SLOW.exists()

    use_test = False
    if has_fast or has_slow:
        use_test = st.sidebar.checkbox("🧪 Использовать тестовые файлы", value=False, key="global_use_test")

    uploaded_file = None
    if not use_test:
        uploaded_file = st.sidebar.file_uploader(
            "Загрузите .xlsx файл",
            type=["xlsx"],
            key="global_upload",
            help="Файл будет доступен на всех страницах",
        )

    pipeline_mode = st.sidebar.radio(
        "Режим обработки:",
        ["Базовое решение (fast)", "AI-решение (slow)"],
        key="global_pipeline_mode",
    )

    load_btn = st.sidebar.button("📥 Загрузить данные", key="global_load_btn")

    if load_btn:
        os.makedirs(RAW_DIR, exist_ok=True)

        if use_test:
            src_path = TEST_FILE_SLOW if pipeline_mode == "AI-решение (slow)" else TEST_FILE_FAST
            if src_path.exists():
                import shutil
                shutil.copy(str(src_path), str(TEMP_UPLOAD_PATH))
                source_name = src_path.name
                st.sidebar.success(f"✅ Тестовый файл: {source_name}")
            else:
                st.sidebar.error(f"❌ Тестовый файл не найден: {src_path}")
                return None, "", ""
        elif uploaded_file is not None:
            with open(TEMP_UPLOAD_PATH, "wb") as f:
                f.write(uploaded_file.getbuffer())
            source_name = uploaded_file.name
            st.sidebar.success(f"✅ Загружен: {source_name}")
        else:
            st.sidebar.warning("⚠️ Выберите файл для загрузки")
            return None, "", ""

        # Загружаем как Polars
        try:
            df = pl.read_excel(str(TEMP_UPLOAD_PATH), engine="calamine")
            set_raw_data(df, source_name)
            st.session_state[SESSION_KEY]["pipeline_mode"] = pipeline_mode
            st.sidebar.success(f"📊 {len(df)} записей, {len(df.columns)} колонок")
            st.rerun()  # перерисовываем, чтобы показать статус загрузки
        except Exception as e:
            st.sidebar.error(f"❌ Ошибка чтения: {e}")
            return None, "", ""

    return None, "", ""