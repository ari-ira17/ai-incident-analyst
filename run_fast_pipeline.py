import polars as pl
import os
import json
from datetime import datetime

# Пути относительно корня проекта
INPUT_FILE = "data/raw/тестовый файл.xlsx" 
OUTPUT_FILE = "data/processed/тестовый_файл_slow.csv"
RANKS_JSON_FILE = "data/reference/problem_rating.json" 

def run_fast_processing(input_path: str = INPUT_FILE, output_path: str = OUTPUT_FILE):
    print("Этап 1: Чтение большого файла через Polars (Calamine)...")
    df = pl.read_excel(input_path, engine="calamine")
    
    print("Этап 2: Создание колонки is_problem (все исходные столбцы сохранены)...")
    if "Тип инцидента" in df.columns:
        processed_df = df.with_columns(
            pl.when(pl.col("Тип инцидента").is_in(["Решаемый", "Не решаемый"]))
            .then(1)
            .otherwise(0)
            .cast(pl.Int32)
            .alias("is_problem")
        )
    else:
        print("Предупреждение: Колонка 'Тип инцидента' не найдена.")
        processed_df = df.with_columns(pl.lit(0).cast(pl.Int32).alias("is_problem"))
    
    print("Этап 3: Добавление колонки severity из JSON...")
    if "Тема" in processed_df.columns and os.path.exists(RANKS_JSON_FILE):
        with open(RANKS_JSON_FILE, "r", encoding="utf-8") as f:
            ranks_dict = json.load(f)
        
        processed_df = processed_df.with_columns(
            pl.col("Тема")
            .replace_strict(ranks_dict, default=1)
            .cast(pl.Int32)
            .alias("severity")
        )
    else:
        print(f"Предупреждение: Справочник или колонка 'Тема' не найдены. Установлен дефолт 1.")
        processed_df = processed_df.with_columns(
            pl.lit(1).cast(pl.Int32).alias("severity")
        )
    
    print("Этап 4: Обработка пустых значений и форматов...")
    
    # 4.1. Обработка времени в datetime (если пусто — ставим 1970-01-01)
    time_col = "Время с начала создания инцидента до окончания"
    if time_col in processed_df.columns:
        dtype_str = str(processed_df.schema[time_col]).lower()
        
        if "duration" in dtype_str:
            processed_df = processed_df.with_columns(
                pl.col(time_col)
                .dt.total_milliseconds()
                .cast(pl.Datetime("ms"))
                .fill_null(datetime(1970, 1, 1))
            )
        elif "datetime" in dtype_str or "date" in dtype_str:
            processed_df = processed_df.with_columns(
                pl.col(time_col).fill_null(datetime(1970, 1, 1))
            )
        else:
            processed_df = processed_df.with_columns(
                pl.col(time_col)
                .cast(pl.Datetime, strict=False)
                .fill_null(datetime(1970, 1, 1))
            )
            
    # 4.2. Обработка абсолютно всех остальных колонок файла
    # Исключаем из массовой обработки колонку времени и созданные признаки
    excluded_cols = [time_col, "is_problem", "severity"]
    other_cols = [col for col in processed_df.columns if col not in excluded_cols]
    
    if other_cols:
        print(f"Заполнение пустых ячеек в остальных колонках ({len(other_cols)} шт.) значением 'Не известно'...")

        # Разделим колонки по типу: Duration и всё остальное
        dur_cols = [c for c in other_cols if processed_df.schema[c] == pl.Duration]
        str_cols = [c for c in other_cols if c not in dur_cols]

        # 1. Обработка Duration-колонок
        if dur_cols:
            processed_df = processed_df.with_columns([
                pl.when(pl.col(c).is_null())
                .then(pl.lit("Не известно"))
                .otherwise(
                    # Превращаем Duration в миллисекунды → строку
                    pl.col(c).dt.total_milliseconds().cast(pl.String)
                )
                .alias(c)
                for c in dur_cols
            ])

        # 2. Обработка всех остальных колонок
        if str_cols:
            processed_df = processed_df.with_columns([
                pl.when(pl.col(c).is_null() | (pl.col(c).cast(pl.String) == ""))
                .then(pl.lit("Не известно"))
                .otherwise(pl.col(c).cast(pl.String))
                .alias(c)
                for c in str_cols
            ])
    
    print("Этап 5: Сохранение результата в единый CSV...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    processed_df.write_csv(output_path, include_header=True)
    print(f"Работа окончена. Все исходные колонки и новые признаки сохранены в: {output_path}")
    
    return output_path

if __name__ == "__main__":
    run_fast_processing()
    