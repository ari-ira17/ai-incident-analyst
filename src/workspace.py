"""
src/workspace.py
────────────────
Единый файловый менеджер (workspace) для всех страниц приложения.
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
    "raw": "Исходные файлы",
    "classified": "Классифицированные данные",
    "analyzed": "Обработанные данные (Severity)",
    "generated": "Сгенерированные ответы",
    "reports": "Аналитические отчеты",
}

PAGE_FOLDER_MAP = {
    "classificator": "raw",
    "analyst": "classified",
    "generator": "classified",
    "map": "analyzed",
}

TEST_FILES = {
    "Тестовый файл (fast)": "data/raw/тестовый файл.xlsx",
    "Тестовый файл (slow)": "data/raw/test_40.xlsx",
    "Тестовый файл (classifier)": "data/raw/text_classifier_data.xlsx",
}

# ---------------------------------------------------------------------------
# FileManager — работа с файловой системой
# ---------------------------------------------------------------------------

class FileManager:
    def __init__(self, workspace_dir: str = WORKSPACE_DIR):
        self.workspace_dir = workspace_dir
        self._ensure_folders()

    def _ensure_folders(self):
        for folder in FOLDERS:
            os.makedirs(os.path.join(self.workspace_dir, folder), exist_ok=True)

    def list_files(self, folder: str) -> list[str]:
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
        return os.path.join(self.workspace_dir, folder, filename)

    def upload_file(self, folder: str, uploaded_file) -> str | None:
        if uploaded_file is None:
            return None
        folder_path = os.path.join(self.workspace_dir, folder)
        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path

    def delete_file(self, folder: str, filename: str):
        file_path = os.path.join(self.workspace_dir, folder, filename)
        if os.path.exists(file_path):
            os.remove(file_path)

    def copy_test_files(self):
        copied = []
        for label, src_rel in TEST_FILES.items():
            src = os.path.join(PROJECT_ROOT, src_rel)
            if os.path.exists(src):
                dst = os.path.join(self.workspace_dir, "raw", os.path.basename(src))
                shutil.copy2(src, dst)
                copied.append(label)
        return copied

    def get_output_path(self, folder: str, filename: str) -> str:
        folder_path = os.path.join(self.workspace_dir, folder)
        os.makedirs(folder_path, exist_ok=True)
        return os.path.join(folder_path, filename)

    def read_file_bytes(self, folder: str, filename: str) -> bytes | None:
        file_path = os.path.join(self.workspace_dir, folder, filename)
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                return f.read()
        return None

    def get_mime_type(self, filename: str) -> str:
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
    if WORKSPACE_KEY not in st.session_state:
        st.session_state[WORKSPACE_KEY] = {
            "raw_file": None,
            "classified_file": None,
            "analyzed_file": None,
            "generated_file": None,
        }

def get_workspace() -> dict:
    init_workspace()
    return st.session_state[WORKSPACE_KEY]

def set_workspace_file(folder: str, file_path: str):
    ws = get_workspace()
    key = f"{folder}_file"
    ws[key] = file_path

# ---------------------------------------------------------------------------
# Отрисовка панели
# ---------------------------------------------------------------------------

def render_workspace_panel(active_page: str = None):
    init_workspace()
    fm = FileManager()
    ws = get_workspace()

    # Прокачанные корпоративные стили
    st.markdown("""
    <style>
        div[data-testid="stColumn"]:has(.ws-title) {
            border-left: 1px solid rgba(128, 128, 128, 0.2);
            padding-left: 1.5rem !important;
        }
        .ws-title {
            font-size: 1.3rem;
            font-weight: 700;
            margin-bottom: 0.1rem;
            letter-spacing: -0.01em;
        }
        .ws-folder-title {
            font-size: 0.85rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            margin-top: 1.25rem;
            margin-bottom: 0.5rem;
        }
        .ws-folder-active {
            color: #0f62fe !important;
            border-bottom: 1px dashed rgba(15, 98, 254, 0.4);
            display: inline-block;
        }
        
        /* СТИЛИЗАЦИЯ КНОПОК ФАЙЛОВ */
        /* Нацеливаемся на обертку кнопок внутри Workspace, чтобы не сломать кнопки на главном экране */
        div[data-testid="stColumn"]:has(.ws-title) div[data-testid="stButton"] button {
            border-radius: 4px !important;
            font-size: 0.85rem !important;
            padding: 0.35rem 0.5rem !important;
            height: auto !important;
        }
        
        /* Специфичный хак для ПЕРЕОПРЕДЕЛЕНИЯ яркой "primary" кнопки Streamlit */
        div[data-testid="stColumn"]:has(.ws-title) div[data-testid="stButton"] button[data-testid="baseButton-primary"] {
            background-color: rgba(15, 98, 254, 0.15) !important; /* Полупрозрачный строгий синий */
            color: #74a3ff !important; /* Мягкий не утомляющий текст */
            border: 1px solid rgba(15, 98, 254, 0.5) !important; /* Аккуратная рамка */
            box-shadow: none !important;
        }
        
        div[data-testid="stColumn"]:has(.ws-title) div[data-testid="stButton"] button[data-testid="baseButton-primary"]:hover {
            background-color: rgba(15, 98, 254, 0.25) !important;
            color: #fff !important;
            border-color: #0f62fe !important;
        }

        /* Скачивание файлов — делаем шрифт моноширинным и аккуратным */
        div[data-testid="stColumn"]:has(.ws-title) div[data-testid="stDownloadButton"] button {
            font-family: monospace !important;
            font-size: 0.8rem !important;
            background-color: transparent !important;
            border: 1px solid rgba(128, 128, 128, 0.2) !important;
            color: gray !important;
            padding: 0.35rem 0.2rem !important;
        }
        div[data-testid="stColumn"]:has(.ws-title) div[data-testid="stDownloadButton"] button:hover {
            border-color: rgba(128, 128, 128, 0.5) !important;
            color: var(--text-color) !important;
        }

        .ws-status-container {
            background-color: var(--secondary-background-color);
            border: 1px solid rgba(128, 128, 128, 0.2);
            border-radius: 4px;
            padding: 1rem;
            margin-top: 1.5rem;
        }
        .status-tag {
            font-family: monospace;
            font-size: 0.75rem;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 3px;
            text-transform: uppercase;
        }
        .status-ready { background-color: rgba(36, 161, 72, 0.15); color: #24a148; }
        .status-wait { background-color: rgba(241, 196, 15, 0.15); color: #b7950b; }
        .status-none { background-color: rgba(128, 128, 128, 0.15); color: gray; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='ws-title'>Workspace</div>", unsafe_allow_html=True)
    st.caption("Файловый менеджер проекта")

    # Заякоренная зона загрузки
    uploaded = st.file_uploader(
        "Загрузить новый реестр в систему",
        type=["xlsx", "xls", "csv"],
        key="ws_fixed_global_uploader",
    )
    if uploaded is not None:
        path = fm.upload_file("raw", uploaded)
        if path:
            ws["raw_file"] = path
            st.rerun()

    st.markdown("<div style='margin-top:1rem; border-bottom:1px solid rgba(128,128,128,0.1);'></div>", unsafe_allow_html=True)

    active_folder = PAGE_FOLDER_MAP.get(active_page) if active_page else None

    for folder_key, folder_label in FOLDERS.items():
        is_active = folder_key == active_folder
        files = fm.list_files(folder_key)
        ws_key = f"{folder_key}_file"

        if is_active:
            st.markdown(f"<div class='ws-folder-title ws-folder-active'>{folder_label}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='ws-folder-title'>{folder_label}</div>", unsafe_allow_html=True)

        if files:
            for fname in files:
                fpath = fm.get_file_path(folder_key, fname)
                is_selected = ws.get(ws_key) == fpath

                # Идеальная пропорция колонок, чтобы кнопки скачивания не ломались по буквам
                cols = st.columns([5, 2])
                with cols[0]:
                    prefix = "[x] " if is_selected else "[ ] "
                    label = f"{prefix}{fname}"

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
                            label="CSV" if fname.lower().endswith(".csv") else "XLSX",
                            data=file_bytes,
                            file_name=fname,
                            mime=fm.get_mime_type(fname),
                            key=f"ws_dl_{folder_key}_{fname}",
                            use_container_width=True,
                        )
        else:
            st.markdown("<div style='font-size:0.85rem; color:gray; font-style:italic; padding-left:2px;'>Реестр пуст</div>", unsafe_allow_html=True)

        st.markdown("<div style='margin-top:0.75rem; border-bottom:1px solid rgba(128,128,128,0.1);'></div>", unsafe_allow_html=True)

    # Тестовые данные
    test_raw_dir = os.path.join(PROJECT_ROOT, "data", "raw")
    if os.path.exists(test_raw_dir) and any(f.endswith((".xlsx", ".xls")) for f in os.listdir(test_raw_dir)):
        st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
        if st.button("Инициализировать тесты", use_container_width=True, type="secondary"):
            copied = fm.copy_test_files()
            if copied:
                st.rerun()

    # Статус конвейера
    st.markdown("<div class='ws-folder-title' style='margin-top:2rem;'>Статус конвейера</div>", unsafe_allow_html=True)
    
    status_config = {
        "raw_file": ("Исходный реестр", "Загружен", "Отсутствует"),
        "classified_file": ("Классификация", "Выполнена", "В очереди"),
        "analyzed_file": ("Анализ Severity", "Выполнен", "В очереди"),
        "generated_file": ("Синтез ответов", "Выполнен", "В очереди"),
    }
    
    st.markdown("<div class='ws-status-container'>", unsafe_allow_html=True)
    for key, (label, text_ready, text_wait) in status_config.items():
        val = ws.get(key)
        if val:
            fname = os.path.basename(val)
            tag_html = f"<span class='status-tag status-ready'>{text_ready}</span>"
            st.markdown(f"<div style='font-size:0.85rem; margin-bottom:0.4rem;'>{tag_html} <b>{label}:</b> <code style='font-size:0.75rem;'>{fname}</code></div>", unsafe_allow_html=True)
        else:
            is_raw = (key == "raw_file")
            style_class = "status-none" if is_raw else "status-wait"
            status_text = text_wait
            
            tag_html = f"<span class='status-tag {style_class}'>{status_text}</span>"
            st.markdown(f"<div style='font-size:0.85rem; margin-bottom:0.4rem; color:gray;'>{tag_html} {label}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)