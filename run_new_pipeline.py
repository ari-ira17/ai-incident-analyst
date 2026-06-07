import pandas as pd
import time
from src.preprocessing.cleaner import IncidentDataCleaner
from src.llm.batcher import create_batches
from src.llm.new_classifier import classify_new_incidents_batch
from run_pipeline import extract_and_clean

INPUT_FILE = "data/raw/test_40.xlsx"
CLEANED_FILE = "data/processed/test_40_cleaned.csv"
NEW_CLASSIFIED_FILE = "data/processed/test_40_predictions.csv"

def main():
    extract_and_clean()
    print("Этап 2. Запуск нового пайплайна предсказания служб и тем...")
    
    # Загружаем уже очищенные данные
    df = pd.read_csv(CLEANED_FILE)
    df["incident_id"] = range(len(df))
    
    records = df.to_dict(orient="records")
    all_results = []

    for batch_number, batch in enumerate(create_batches(records, batch_size=3), start=1):
        print(f"Обрабатывается батч {batch_number}")
        try:
            result = classify_new_incidents_batch(batch)
            all_results.extend(result)
            time.sleep(2) # Защита от перегрева
        except Exception as e:
            print(f"Ошибка в батче {batch_number}: {e}")
            # Дефолтная заглушка в случае сбоя JSON
            for row in batch:
                all_results.append({
                    "incident_id": row["incident_id"],
                    "is_problem": 1,
                    "topic": "Не определено",
                    "department": "Дежурная служба"
                })

    # Собираем результаты
    result_df = pd.DataFrame(all_results)
    
    # Соединяем исходный датафрейм с предсказаниями модели
    final_df = df.merge(result_df, on="incident_id", how="left")
    
    # Сохраняем итоговый файл, который пойдет в Streamlit
    final_df.to_csv(NEW_CLASSIFIED_FILE, index=False, encoding="utf-8-sig")
    print(f"Новые предсказания успешно сохранены в: {NEW_CLASSIFIED_FILE}")

if __name__ == "__main__":
    main()
