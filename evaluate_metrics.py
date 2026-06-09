"""
Оценка качества модели на тестовых данных.
"""

import pandas as pd
import json
from sklearn.metrics import (
    accuracy_score, 
    precision_score, 
    recall_score, 
    f1_score,
    confusion_matrix,
    classification_report
)

def load_mappings():
    """Загружает оба маппинга"""
    with open("data/dept_mapping_omsk.json", "r", encoding="utf-8") as f:
        omsk_mapping = json.load(f)
    
    with open("data/dept_mapping_region.json", "r", encoding="utf-8") as f:
        region_mapping = json.load(f)
    
    return omsk_mapping, region_mapping

def get_ground_truth_dept(row, omsk_mapping, region_mapping):
    """
    Возвращает правильный отдел.
    Логика: сначала пробуем найти тему в omsk_mapping (для Омска),
    если не нашлось - пробуем в region_mapping (для области).
    """
    topic = row.get('Тема', '')
    
    if pd.isna(topic):
        return None
    
    result = omsk_mapping.get(topic, None)
    if result is not None:
        return result
    
    return region_mapping.get(topic, None)

def evaluate_is_problem(df):
    """Оценка определения is_problem по типу инцидента"""
    
    df['ground_truth'] = df['Тип инцидента'].apply(
        lambda x: 1 if str(x) in ["Решаемый", "Не решаемый"] else 0
    )
    
    eval_df = df[df['is_problem'].notna()]
    
    if len(eval_df) == 0:
        print("Нет данных для оценки is_problem")
        return
    
    y_true = eval_df['ground_truth']
    y_pred = eval_df['is_problem']
    
    print("\nОЦЕНКА МЕТРИК: is_problem")
    print(f"Всего строк в оценке: {len(eval_df)}")
    print(f"\nAccuracy: {accuracy_score(y_true, y_pred):.4f}")
    print(f"Precision: {precision_score(y_true, y_pred):.4f}")
    print(f"Recall: {recall_score(y_true, y_pred):.4f}")
    print(f"F1-score: {f1_score(y_true, y_pred):.4f}")
    
    print("\nМатрица ошибок:")
    cm = confusion_matrix(y_true, y_pred)
    print(f"            Предсказано")
    print(f"           0      1")
    print(f"Реально 0  {cm[0,0]:>5}  {cm[0,1]:>5}")
    print(f"       1  {cm[1,0]:>5}  {cm[1,1]:>5}")
    
    print("\nПодробный отчёт:")
    print(classification_report(y_true, y_pred, 
                                target_names=['Не проблема', 'Проблема']))

def evaluate_topic(df):
    """Оценка определения темы (по маппингу отделов)"""
    
    omsk_mapping, region_mapping = load_mappings()
    
    df['ground_truth_dept'] = df.apply(
        lambda row: get_ground_truth_dept(row, omsk_mapping, region_mapping),
        axis=1
    )
    
    missing = df[df['ground_truth_dept'].isna() & df['Тема'].notna()]
    if len(missing) > 0:
        print(f"\nВНИМАНИЕ: {len(missing)} строк не найдено в маппинге")
        print("Примеры (темы, которых нет ни в одном маппинге):")
        for _, row in missing.head(10).iterrows():
            print(f"  Тема: {row['Тема']} | Муниципалитет: {row['Муниципалитет']}")
    
    eval_df = df[(df['ground_truth_dept'].notna()) & (df['department'].notna())]
    
    if len(eval_df) == 0:
        print("\nНет данных для оценки topic")
        return
    
    correct = (eval_df['department'] == eval_df['ground_truth_dept']).sum()
    total = len(eval_df)
    
    print("\nОЦЕНКА МЕТРИК: topic → department")
    print(f"Всего строк в оценке: {total}")
    print(f"Правильных отделов: {correct}")
    print(f"Accuracy: {correct/total:.4f}")
    

def evaluate_speed(df, total_time_seconds):
    """Оценка скорости обработки"""
    
    total_rows = len(df)
    print("\nОЦЕНКА СКОРОСТИ")
    print(f"Всего строк: {total_rows}")
    print(f"Общее время: {total_time_seconds:.2f} сек")
    print(f"Скорость: {total_time_seconds/total_rows:.3f} сек/строку")
    print(f"Строк в час: {int(total_rows / total_time_seconds * 3600)}")

def main():
    df = pd.read_csv("data/processed/final_predictions.csv")
    print(f"Загружено строк: {len(df)}")
    
    evaluate_is_problem(df)
    
    evaluate_topic(df)
    
    pipeline_time = 300 
    evaluate_speed(df, pipeline_time)

if __name__ == "__main__":
    main()