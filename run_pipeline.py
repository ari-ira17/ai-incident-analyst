import pandas as pd
import os

from src.ingestion.excel_reader import read_excel
from src.ingestion.csv_exporter import save_to_csv
from src.preprocessing.cleaner import IncidentDataCleaner

from src.llm.batcher import create_batches
from src.llm.classifier import classify_batch


INPUT_FILE = "data/raw/test_40.xlsx"

CLEANED_FILE = "data/processed/test_40_cleaned.csv"

CLASSIFIED_FILE = "data/processed/test_40_classified.csv"


def extract_and_clean():

    print("Этап 1. Загрузка и очистка")

    raw_data = read_excel(INPUT_FILE)

    df = pd.DataFrame(raw_data)

    cleaner = IncidentDataCleaner(df)

    cleaned_df = (
        cleaner
        .show_basic_stats()
        .remove_duplicates()
        .convert_duration_column()
        .handle_missing_values()
        .clean_text_formatting()
        .get_dataframe()
    )

    cleaned_data = cleaned_df.to_dict(
        orient="records"
    )

    save_to_csv(
        cleaned_data,
        CLEANED_FILE
    )

    print(
        f"Файл сохранён: {CLEANED_FILE}"
    )

    return cleaned_df


def classify_incidents(df):

    print("Этап 2. Классификация")

    df = df.copy()

    df["incident_id"] = range(len(df))

    records = df.to_dict(
        orient="records"
    )

    all_results = []

    for batch_number, batch in enumerate(
        create_batches(records, batch_size=5),
        start=1
    ):

        print(
            f"Обрабатывается батч {batch_number}"
        )

        try:

            result = classify_batch(batch)

            all_results.extend(result)

        except Exception as e:

            print(
                f"Ошибка батча {batch_number}: {e}"
            )

    result_df = pd.DataFrame(all_results)

    final_df = df.merge(
        result_df,
        on="incident_id",
        how="left"
    )

    final_df.to_csv(
        CLASSIFIED_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    print(
        f"Результат сохранён: {CLASSIFIED_FILE}"
    )


def main():

    cleaned_df = extract_and_clean()

    classify_incidents(cleaned_df)

    print("Pipeline завершён")


def run_full_slow_pipeline(input_excel: str, output_csv: str):
    """
    Выполняет медленный пайплайн:
    1. Чтение, очистка, сохранение очищенных данных (промежуточно).
    2. Классификация батчами.
    3. Сохранение итогового классифицированного CSV в output_csv.
    """
    raw_data = read_excel(input_excel)
    df = pd.DataFrame(raw_data)
    cleaner = IncidentDataCleaner(df)
    cleaned_df = (cleaner
                  .show_basic_stats()
                  .remove_duplicates()
                  .convert_duration_column()
                  .handle_missing_values()
                  .clean_text_formatting()
                  .get_dataframe())
    df2 = cleaned_df.copy()
    df2["incident_id"] = range(len(df2))
    records = df2.to_dict(orient="records")

    all_results = []
    for batch_number, batch in enumerate(
        create_batches(records, batch_size=5), start=1
    ):
        print(f"Обрабатывается батч {batch_number}")
        try:
            result = classify_batch(batch)
            all_results.extend(result)
        except Exception as e:
            print(f"Ошибка батча {batch_number}: {e}")

    result_df = pd.DataFrame(all_results)
    final_df = df2.merge(result_df, on="incident_id", how="left")

    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    final_df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"Итоговый файл сохранён: {output_csv}")

if __name__ == "__main__":
    run_full_slow_pipeline(INPUT_FILE, CLASSIFIED_FILE)
