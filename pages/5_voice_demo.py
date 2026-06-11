import streamlit as st
import speech_recognition as sr
import tempfile
import os
from pathlib import Path
import pandas as pd
from datetime import datetime

from src.workspace import render_workspace_panel, init_workspace, FileManager

st.set_page_config(
    page_title="Голосовой ввод | AI-аналитик",
    page_icon="🎤",
    layout="wide"
)

st.markdown("""
<style>
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
    color:gray;
    font-size:1rem;
    padding-bottom:1rem;
    border-bottom:1px solid rgba(120,120,120,.2);
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">

<div class="page-badge">
VOICE PROCESSING MODULE
</div>

<div class="title-row">
    <div class="title-bar"></div>
    <h1 class="page-title">
        Голосовой ввод обращений
    </h1>
</div>

<div class="page-subtitle">
Распознавание речи и формирование обращений граждан для последующей обработки системой
</div>

</div>
""", unsafe_allow_html=True)

init_workspace()

left_col, right_col = st.columns([3, 1])

with right_col:
    render_workspace_panel(active_page="voice")

with left_col:

    if "recognized_texts" not in st.session_state:
        st.session_state.recognized_texts = []

    st.markdown("---")
    st.markdown("### ⚙️ Как работает голосовой ввод")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
        <div style="
            background: var(--secondary-background-color);
            border-radius: 12px;
            padding: 1rem;
            text-align: center;
            border: 1px solid rgba(15,98,254,.2);
        ">
            <div style="font-size:1.8rem;font-weight:700;color:#0f62fe;">1</div>
            <div style="font-weight:700;">Загрузка файла</div>
            <div style="font-size:.8rem;opacity:.7;">
                WAV-аудио обращения
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="
            background: var(--secondary-background-color);
            border-radius: 12px;
            padding: 1rem;
            text-align: center;
            border: 1px solid rgba(15,98,254,.2);
        ">
            <div style="font-size:1.8rem;font-weight:700;color:#0f62fe;">2</div>
            <div style="font-weight:700;">Распознавание</div>
            <div style="font-size:.8rem;opacity:.7;">
                Google Speech API
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div style="
            background: var(--secondary-background-color);
            border-radius: 12px;
            padding: 1rem;
            text-align: center;
            border: 1px solid rgba(15,98,254,.2);
        ">
            <div style="font-size:1.8rem;font-weight:700;color:#0f62fe;">3</div>
            <div style="font-weight:700;">Формирование текста</div>
            <div style="font-size:.8rem;opacity:.7;">
                Создание обращения
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown("""
        <div style="
            background: var(--secondary-background-color);
            border-radius: 12px;
            padding: 1rem;
            text-align: center;
            border: 1px solid rgba(15,98,254,.2);
        ">
            <div style="font-size:1.8rem;font-weight:700;color:#0f62fe;">4</div>
            <div style="font-weight:700;">Экспорт</div>
            <div style="font-size:.8rem;opacity:.7;">
                Сохранение в Excel
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("### Загрузите WAV-файл с жалобой")
    
    audio_file = st.file_uploader(
        "Выберите аудиофайл",
        type=["wav"],
        help="Поддерживается только формат WAV. Рекомендации: моно, 16 kHz, 16-bit"
    )
    
    if audio_file:
        st.audio(audio_file, format="audio/wav")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🎙️ Распознать речь", type="primary", use_container_width=True):
                with st.spinner("🔄 Распознавание речи..."):
                    # Сохраняем временный файл
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                        tmp_file.write(audio_file.read())
                        tmp_path = tmp_file.name
                    
                    recognizer = sr.Recognizer()
                    
                    try:
                        with sr.AudioFile(tmp_path) as source:
                            recognizer.adjust_for_ambient_noise(source)
                            audio = recognizer.record(source)
                            text = recognizer.recognize_google(audio, language="ru-RU")
                        
                        st.success(f"✅ Распознанный текст:\n> {text}")
                        
                        # Добавляем в список
                        st.session_state.recognized_texts.append({
                            "Текст инцидента": text,
                            "Исходный файл": audio_file.name,
                            "Дата распознавания": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        
                        st.info(f"Всего распознано: {len(st.session_state.recognized_texts)} жалоб")
                        
                    except sr.UnknownValueError:
                        st.error("❌ Не удалось распознать речь. Попробуйте другой файл или говорите чётче.")
                    except sr.RequestError as e:
                        st.error(f"❌ Ошибка сервиса распознавания: {e}. Проверьте интернет.")
                    except Exception as e:
                        st.error(f"Ошибка: {e}")
                    
                    # Удаляем временный файл
                    os.unlink(tmp_path)
        
        with col2:
            if st.button("Сохранить аудиофайл (без распознавания)", use_container_width=True):
                fm = FileManager()
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_filename = f"voice_{timestamp}_{audio_file.name}"
                save_path = fm.get_output_path("raw", safe_filename)
                
                # Сохраняем файл
                audio_file.seek(0)
                with open(save_path, "wb") as f:
                    f.write(audio_file.read())
                
                st.success(f"Аудиофайл сохранён: {safe_filename}")
                st.info(f"Путь: {save_path}")

    # ============================================================
    # СПИСОК РАСПОЗНАННЫХ ТЕКСТОВ
    # ============================================================
    st.markdown("---")
    st.markdown("### Список распознанных жалоб")
    
    if st.session_state.recognized_texts:
        df_list = pd.DataFrame(st.session_state.recognized_texts)
        st.dataframe(df_list, use_container_width=True)
        
        col_export, col_clear = st.columns(2)
        
        with col_export:
            if st.button("📊 Сохранить всё в Excel", type="primary", use_container_width=True):
                fm = FileManager()
                
                export_df = pd.DataFrame(st.session_state.recognized_texts)
                
                # Сохраняем в папку "classified" с именем voice_problem_дата.xlsx
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"voice_problem_{timestamp}.xlsx"
                export_path = fm.get_output_path("classified", filename)
                
                export_df.to_excel(export_path, index=False, engine='openpyxl')
                
                st.success(f"✅ Файл сохранён в папку «Классифицированные»: {filename}")
                
                with open(export_path, "rb") as f:
                    st.download_button(
                        label="Скачать Excel файл",
                        data=f.read(),
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        
        with col_clear:
            if st.button("🗑️ Очистить список", use_container_width=True):
                st.session_state.recognized_texts = []
                st.rerun()
    else:
        st.info("Пока нет распознанных жалоб. Загрузите WAV-файл и нажмите 'Распознать речь'.")

    # ============================================================
    # ТЕКСТОВЫЙ ВВОД (для теста)
    # ============================================================
    with st.expander("Или введите текст вручную (для теста)"):
        manual_text = st.text_area("Текст жалобы:", height=80)
        if st.button("➕ Добавить текст в список"):
            if manual_text.strip():
                st.session_state.recognized_texts.append({
                    "Текст инцидента": manual_text.strip(),
                    "Исходный файл": "Введён вручную",
                    "Дата распознавания": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                st.success("✅ Добавлено!")
                st.rerun()

    st.markdown("---")
    st.caption("**Требуется интернет** для распознавания речи (Google Speech Recognition)")
    st.caption("**Формат:** только WAV (рекомендуется: моно, 16 kHz, 16-bit)")

    # Инструкция по конвертации
    with st.expander("Как конвертировать MP3 в WAV"):
        st.markdown("""
        **Бесплатные онлайн-конвертеры:**
        - [Online Audio Converter](https://online-audio-converter.com/ru/)
        - [Convertio](https://convertio.co/ru/mp3-wav/)
        
        **Параметры для WAV:**
        - Кодек: PCM
        - Каналы: Моно
        - Частота: 16000 Hz (16 kHz)
        - Битность: 16 bit
        """)

    # Пример WAV файла
    with st.expander("Где взять тестовый WAV файл?"):
        st.markdown("""
        1. Запишите голос через диктофон на телефоне
        2. Скачайте как WAV
        3. Или используйте любой онлайн-конвертер MP3 → WAV
        """)