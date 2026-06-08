import pandas as pd

def load_unique_topics_and_departments(file_path="data/raw/тестовый файл.xlsx"):
    """Загружает уникальные значения тем и отделов из Excel"""
    df = pd.read_excel(file_path)
    
    unique_topics = df["Тема"].dropna().unique().tolist()
    unique_departments = df["Отдел"].dropna().unique().tolist()
    
    unique_topics.sort()
    unique_departments.sort()
    
    print(f"Загружено уникальных тем: {len(unique_topics)}")
    print(f"Загружено уникальных отделов: {len(unique_departments)}")
    
    return unique_topics, unique_departments