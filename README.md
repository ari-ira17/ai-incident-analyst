# ai-incident-analyst

1. `git clone https://github.com/ari-ira17/ai-incident-analyst`
2. `python3 run_pipeline.py` - `run_pipeline.py` возвращает из xls файла csv с нужными нам столбцами без дубликатов и пропусками обработанными как "Не известно", если это время то там 0. xls лежит в `data/raw/`, а csv `data/processed/`. сейчас там для примера лежат первые 40 строк + заголовки тестового файла. потом будем указывать путь к файлам, с которыми работаем

### Структура проекта (на момент 6.06 в 11:25):
```
incident-ai-analyst/
│
├── src/
│ ├── ingestion/
│ │ ├── excel_reader.py
│ │ ├── csv_exporter.py
│ │ └── schema.py
│ │
│ ├── preprocessing/
│ │ ├── __init__.py
│ │ └── cleaner.py
│ │
│ ├── llm/
│ │ ├── batcher.py
│ │ ├── classifier.py
│ │ └── llama_client.py
│ │
│ └── reports/  (пустая директория для генерации отчётов)
│
├── data/
│ ├── raw/
│ ├── processed/
│ └── reports/
│
├── scripts/
│ ├── extract.py
│ └── classify.py
│
├── run_pipeline.py
├── requirements.txt
```

