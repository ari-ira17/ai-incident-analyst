"""
src/workspace.py
────────────────
Единый файловый менеджер (workspace) для всех страниц приложения.

Пользователь загружает файлы в workspace и сам выбирает,
с каким файлом работать на каждой странице.

Структура workspace:
  workspace/
    raw/          — исходные файлы (загружает пользователь)
    classified/   — после LLM-классификации
    analyzed/     — после pipeline с severity
    generated/    — после генерации ответов
    reports/      — отчёты аналитика
"""

import os
import shutil
import streamlit as st
from pathlib import Path

# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = os.path.join(PROJECT_ROOT, "workspace")

FOLDERS = {
    "raw": "📁 Исходные файлы",
    "classified": "📁 Классифицированные",
    "analyzed": "📁 Обработанные (с severity)",
    "generated": "📁 Сгенерированные ответы",
    "reports": "📁 Отчёты",
}

# Какая страница работает с какой папкой (для подсветки)
PAGE_FOLDER_MAP = {
    "classificator": "raw",
    "analyst": "classified",
    "generator": "classified",
    "map": "analyzed",
}

# Тестовые файлы (копируются из data/raw/)
TEST_FILES = {
    "Тестовый файл (fast)": "data/raw/тестовый файл.xlsx",
    "Тестовый файл (slow)": "data/raw/test_40.xlsx",
    "Тестовый файл (classifier)": "data/raw/text_classifier_data.xlsx",
}

# ---------------------------------------------------------------------------
# FileManager — работа с файловой системой
# ---------------------------------------------------------------------------


class FileManager:
    """Операции с файлами в workspace."""

    def __init__(self, workspace_dir: str = WORKSPACE_DIR):
        self.workspace_dir = workspace_dir
        self._ensure_folders()

    def _ensure_folders(self):
        """Создаёт все папки workspace при инициализации."""
        for folder in FOLDERS:
            os.makedirs(os.path.join(self.workspace_dir, folder), exist_ok=True)

    def list_files(self, folder: str) -> list[str]:
        """Возвращает список файлов в папке (только .xlsx, .csv, .txt)."""
        folder_path = os.path.join(self.workspace_dir, folder)
        if not os.path.exists(folder_path):
            return []
        extensions = (".xlsx", ".xls", ".csv", ".txt")
        files = []
        for f in sorted(os.listdir(folder_path)):
            if f.lower().endswith(extensions):
                files.append(f)
        return files

    def get_file_path(self, folder: str, filename: str) -> str:
        """Полный путь к файлу в workspace."""
        return os.path.join(self.workspace_dir, folder, filename)

    def upload_file(self, folder: str, uploaded_file) -> str | None:
        """Сохраняет загруженный файл в папку workspace. Возвращает путь."""
        if uploaded_file is None:
            return None
        folder_path = os.path.join(self.workspace_dir, folder)
        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path

    def delete_file(self, folder: str, filename: str):
        """Удаляет файл из workspace."""
        file_path = os.path.join(self.workspace_dir, folder, filename)
        if os.path.exists(file_path):
            os.remove(file_path)

    def copy_test_files(self):
        """Копирует тестовые файлы из data/raw/ в workspace/raw/."""
        copied = []
        for label, src_rel in TEST_FILES.items():
            src = os.path.join(PROJECT_ROOT, src_rel)
            if os.path.exists(src):
                dst = os.path.join(self.workspace_dir, "raw", os.path.basename(src))
                shutil.copy2(src, dst)
                copied.append(label)
        return copied

    def get_output_path(self, folder: str, filename: str) -> str:
        """Возвращает путь для сохранения результата."""
        folder_path = os.path.join(self.workspace_dir, folder)
        os.makedirs(folder_path, exist_ok=True)
        return os.path.join(folder_path, filename)

    def read_file_bytes(self, folder: str, filename: str) -> bytes | None:
        """Читает файл как байты для скачивания."""
        file_path = os.path.join(self.workspace_dir, folder, filename)
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                return f.read()
        return None

    def get_mime_type(self, filename: str) -> str:
        """Определяет MIME-тип по расширению файла."""
        if filename.lower().endswith(".xlsx"):
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        elif filename.lower().endswith(".xls"):
            return "application/vnd.ms-excel"
        elif filename.lower().endswith(".csv"):
            return "text/csv"
        elif filename.lower().endswith(".txt"):
            return "text/plain"
        return "application/octet-stream"


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

WORKSPACE_KEY = "workspace"


def init_workspace():
    """Инициализирует workspace в session_state."""
    if WORKSPACE_KEY not in st.session_state:
        st.session_state[WORKSPACE_KEY] = {
            "raw_file": None,
            "classified_file": None,
            "analyzed_file": None,
            "generated_file": None,
        }


def get_workspace() -> dict:
    """Возвращает словарь workspace из session_state."""
    init_workspace()
    return st.session_state[WORKSPACE_KEY]


def set_workspace_file(folder: str, file_path: str):
    """Устанавливает выбранный файл для папки."""
    ws = get_workspace()
    key = f"{folder}_file"
    ws[key] = file_path


# ---------------------------------------------------------------------------
# Отрисовка workspace (правая панель)
# ---------------------------------------------------------------------------


def render_workspace_panel(active_page: str = None):
    """
    Рендерит workspace в правой колонке.

    Параметры:
        active_page: str — идентификатор текущей страницы
            ('classificator', 'analyst', 'generator', 'map', None для app.py)
    """
    init_workspace()
    fm = FileManager()
    ws = get_workspace()

    st.markdown("## 📂 Workspace")
    st.caption("Файловый менеджер проекта")

    # Определяем, какая папка активна для текущей страницы
    active_folder = PAGE_FOLDER_MAP.get(active_page) if active_page else None

    # Отображаем каждую папку
    for folder_key, folder_label in FOLDERS.items():
        is_active = folder_key == active_folder
        files = fm.list_files(folder_key)
        ws_key = f"{folder_key}_file"

        # Заголовок папки
        if is_active:
            st.markdown(f"**{folder_label}** ←")
        else:
            st.markdown(f"{folder_label}")

        # Список файлов
        if files:
            for fname in files:
                fpath = fm.get_file_path(folder_key, fname)
                is_selected = ws.get(ws_key) == fpath

                # Строка: кнопка выбора + кнопка скачивания
                cols = st.columns([4, 1])
                with cols[0]:
                    if is_selected:
                        label = f"● {fname}"
                    else:
                        label = f"○ {fname}"

                    if st.button(
                        label,
                        key=f"ws_{folder_key}_{fname}",
                        use_container_width=True,
                        type="secondary" if not is_selected else "primary",
                    ):
                        ws[ws_key] = fpath
                        st.rerun()

                with cols[1]:
                    file_bytes = fm.read_file_bytes(folder_key, fname)
                    if file_bytes is not None:
                        st.download_button(
                            label="⬇",
                            data=file_bytes,
                            file_name=fname,
                            mime=fm.get_mime_type(fname),
                            key=f"ws_dl_{folder_key}_{fname}",
                            use_container_width=True,
                        )
        else:
            st.caption("  (пусто)")

        # Кнопка загрузки для raw/
        if folder_key == "raw":
            uploaded = st.file_uploader(
                "Загрузить файл",
                type=["xlsx", "xls", "csv"],
                key=f"ws_upload_{folder_key}",
                label_visibility="collapsed",
            )
            if uploaded is not None:
                path = fm.upload_file(folder_key, uploaded)
                if path:
                    st.success(f"✅ {uploaded.name}")
                    # Автоматически выбираем загруженный файл
                    ws[ws_key] = path
                    st.rerun()

        st.markdown("---")

    # Кнопка копирования тестовых файлов
    test_raw_dir = os.path.join(PROJECT_ROOT, "data", "raw")
    if os.path.exists(test_raw_dir) and any(
        f.endswith((".xlsx", ".xls")) for f in os.listdir(test_raw_dir)
    ):
        if st.button("🔄 Копировать тестовые файлы", use_container_width=True):
            copied = fm.copy_test_files()
            if copied:
                st.success(f"Скопировано: {', '.join(copied)}")
                st.rerun()
            else:
                st.warning("Тестовые файлы не найдены в data/raw/")

    # Статус конвейера
    st.markdown("### 📊 Статус конвейера")
    status_icons = {
        "raw_file": ("📄 Исходный", "✅" if ws.get("raw_file") else "❌"),
        "classified_file": ("🏷 Классифицирован", "✅" if ws.get("classified_file") else "⏳"),
        "analyzed_file": ("📊 Проанализирован", "✅" if ws.get("analyzed_file") else "⏳"),
        "generated_file": ("✉️ Сгенерирован", "✅" if ws.get("generated_file") else "⏳"),
    }
    for key, (label, icon) in status_icons.items():
        val = ws.get(key)
        if val:
            fname = os.path.basename(val)
            st.markdown(f"{icon} **{label}:** `{fname}`")
        else:
            st.markdown(f"{icon} {label}: —")