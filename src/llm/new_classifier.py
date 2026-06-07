import json
from src.llm.stage1_is_problem import classify_is_problem
from src.llm.stage2_topic import classify_topic
from src.llm.stage3_department import classify_department_batch

def classify_new_incidents_batch(batch):
    """
    Полный пайплайн классификации из 3 этапов:
    1. Определяем is_problem (LLM)
    2. Определяем topic (LLM) - только для проблем
    3. Определяем department (правила) - для всех
    """
    
    results_1 = classify_is_problem(batch)
    is_problem_dict = {r["incident_id"]: r["is_problem"] for r in results_1}
    
    problem_batch = [row for row in batch if is_problem_dict.get(row["incident_id"], 0) == 1]
    
    results_2 = classify_topic(problem_batch) if problem_batch else []
    topic_dict = {r["incident_id"]: r["topic"] for r in results_2}
    
    results_3 = classify_department_batch(batch)
    department_dict = {r["incident_id"]: r["department"] for r in results_3}
    
    final_results = []
    for row in batch:
        incident_id = row["incident_id"]
        final_results.append({
            "incident_id": incident_id,
            "is_problem": is_problem_dict.get(incident_id, 0),
            "topic": topic_dict.get(incident_id, ""),
            "department": department_dict.get(incident_id, "Дежурная служба")
        })
    
    return final_results