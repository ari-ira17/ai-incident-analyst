import pandas as pd
import time
from src.llm.batcher import create_batches
from src.llm.stage1_is_problem import classify_is_problem
from src.llm.stage2_topic import classify_topic
from src.llm.stage3_department import add_department_to_csv
from run_pipeline import extract_and_clean

INPUT_FILE = "data/raw/тестовый файл.xlsx"
CLEANED_FILE = "data/processed/test_40_cleaned.csv"
TEMP_TOPICS_FILE = "data/processed/temp_topics.csv"
FINAL_OUTPUT_FILE = "data/processed/final_predictions.csv"


def main():
    extract_and_clean()
    
    df = pd.read_csv(CLEANED_FILE).head(5)
    df["incident_id"] = range(len(df))
    records = df.to_dict(orient="records")
    
    print("\nЭТАП 1: Определение is_problem\n")
    all_problems = []
    
    for batch_number, batch in enumerate(create_batches(records, batch_size=5), start=1):
        print(f"Батч {batch_number} (строк: {len(batch)})")
        try:
            result = classify_is_problem(batch)
            all_problems.extend(result)
            time.sleep(1)
        except Exception as e:
            print(f"Ошибка: {e}")
            for row in batch:
                all_problems.append({
                    "incident_id": row["incident_id"],
                    "is_problem": 1
                })
    
    problem_df = pd.DataFrame(all_problems)
    df = df.merge(problem_df, on="incident_id", how="left")
    
    print("\n=ЭТАП 2: Определение темы для ВСЕХ записей\n")
    all_topics = []
    
    for batch_number, batch in enumerate(create_batches(records, batch_size=5), start=1):
        print(f"Батч {batch_number} (строк: {len(batch)})")
        try:
            result = classify_topic(batch)
            all_topics.extend(result)
            time.sleep(1)
        except Exception as e:
            print(f"Ошибка: {e}")
            for row in batch:
                all_topics.append({
                    "incident_id": row["incident_id"],
                    "topic": "Прочее"
                })
    
    topic_df = pd.DataFrame(all_topics)
    df = df.merge(topic_df, on="incident_id", how="left")
    df['topic'] = df['topic'].fillna("Прочее")
    
    df.to_csv(TEMP_TOPICS_FILE, index=False, encoding="utf-8-sig")
    print(f"\nПромежуточный результат сохранён: {TEMP_TOPICS_FILE}")
    
    print("\nЭТАП 3: Определение отдела\n")
    add_department_to_csv(TEMP_TOPICS_FILE, FINAL_OUTPUT_FILE)
    print(f"Финальный файл: {FINAL_OUTPUT_FILE}")


if __name__ == "__main__":
    main()