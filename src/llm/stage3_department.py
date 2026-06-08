import json
import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
MAPPING_OMSK_PATH = os.path.join(BASE_DIR, "data", "dept_mapping_omsk.json")
MAPPING_REGION_PATH = os.path.join(BASE_DIR, "data", "dept_mapping_region.json")

_MAPPING_OMSK = None
_MAPPING_REGION = None


def _load_mapping_omsk():
    global _MAPPING_OMSK
    if _MAPPING_OMSK is None:
        if os.path.exists(MAPPING_OMSK_PATH):
            with open(MAPPING_OMSK_PATH, encoding="utf-8") as f:
                _MAPPING_OMSK = json.load(f)
        else:
            _MAPPING_OMSK = {}
    return _MAPPING_OMSK


def _load_mapping_region():
    global _MAPPING_REGION
    if _MAPPING_REGION is None:
        if os.path.exists(MAPPING_REGION_PATH):
            with open(MAPPING_REGION_PATH, encoding="utf-8") as f:
                _MAPPING_REGION = json.load(f)
        else:
            _MAPPING_REGION = {}
    return _MAPPING_REGION


def get_department(municipality: str, topic: str) -> str:
    """Определяет отдел по муниципалитету и теме"""
    omsk_mapping = _load_mapping_omsk()
    region_mapping = _load_mapping_region()
    
    if municipality == "Омск г.о.":
        return omsk_mapping.get(topic, "Администрация города Омска")
    
    if municipality == "Омская область, другое":
        return region_mapping.get(topic, "Администрация Омской области")
    
    if municipality and "район" in municipality.lower():
        return f"Администрация {municipality}"
    
    return "Администрация города Омска"


def add_department_to_csv(input_csv: str, output_csv: str = None) -> pd.DataFrame:
    """Добавляет колонку department в CSV файл"""
    df = pd.read_csv(input_csv)
    df['department'] = df.apply(
        lambda row: get_department(str(row.get("Муниципалитет", "")), str(row.get("topic", ""))),
        axis=1
    )
    if output_csv:
        df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    return df


def classify_department_batch(batch: list[dict]) -> list[dict]:
    """Определяет отдел для батча записей"""
    results = []
    for row in batch:
        municipality = str(row.get("Муниципалитет", "")).strip()
        topic = str(row.get("topic", "")).strip()
        department = get_department(municipality, topic)
        results.append({
            "incident_id": row["incident_id"],
            "department": department,
        })
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace(".csv", "_with_dept.csv")
        add_department_to_csv(input_file, output_file)
        print(f"Готово: {output_file}")
    else:
        print("Использование: python stage3_department.py input.csv [output.csv]")