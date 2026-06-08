"""
Сжатие (суммаризация) текстов обращений граждан
с использованием RuT5 multilingual model.

Функция compress_text() принимает сырой текст инцидента
и возвращает его сжатую версию (2-3 предложения).
"""

import re
import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer


MODEL_NAME = "cointegrated/rut5-base-multitask"
MAX_INPUT_TOKENS = 1024
MAX_OUTPUT_TOKENS = 512

_device = None
_tokenizer = None
_model = None


def _lazy_load():
    """Ленивая загрузка модели и токенизатора (один раз при первом вызове)."""
    global _device, _tokenizer, _model
    if _model is not None:
        return
    print(f"Загрузка модели {MODEL_NAME}...")
    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _tokenizer = T5Tokenizer.from_pretrained(MODEL_NAME)
    _model = T5ForConditionalGeneration.from_pretrained(MODEL_NAME)
    _model.to(_device)
    _model.eval()
    print(f"Модель загружена на {_device}")


def _clean_text(text: str) -> str:
    """Очистка текста: удаление URL, @username, [club...], HTML-тегов."""
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\[.*?\|.*?\]", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compress_text(text: str, max_length: int = MAX_OUTPUT_TOKENS) -> str:
    """
    Сжатие текста обращения до 2-3 предложений с помощью RuT5.

    Параметры
    ---------
    text : str
        Исходный текст инцидента.
    max_length : int
        Максимальная длина сжатого текста в токенах (по умолчанию 150).

    Возвращает
    ----------
    str
        Сжатая версия текста.
    """
    _lazy_load()

    cleaned = _clean_text(text)

    if not cleaned or len(cleaned.split()) < 5:
        return text

    # Префикс "Суммаризация:" активирует режим суммаризации для rut5-base-multitask
    input_text = f"Суммаризация: {cleaned}"

    inputs = _tokenizer(
        input_text,
        return_tensors="pt",
        truncation=True,
        max_length=MAX_INPUT_TOKENS,
    ).to(_device)

    with torch.no_grad():
        outputs = _model.generate(
            **inputs,
            max_length=max_length,
            min_length=30,
            num_beams=3,
            length_penalty=1.2,
            early_stopping=True,
            no_repeat_ngram_size=3,
        )

    summary = _tokenizer.decode(outputs[0], skip_special_tokens=True)
    return summary.strip()


def compress_batch(texts: list[str], max_length: int = MAX_OUTPUT_TOKENS) -> list[str]:
    """Сжатие списка текстов."""
    return [compress_text(t, max_length=max_length) for t in texts]