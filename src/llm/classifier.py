import json
from src.llm.llama_client import generate
import re


def classify_batch(batch):
    llm_input = []
    
    for row in batch:
        llm_input.append({
            "incident_id": row["incident_id"],
            "group": str(row.get("Группа тем", "")),
            "topic": str(row.get("Тема", "")),
            "text": str(row.get("Текст инцидента", ""))
        })
    
    prompt = f"""Determine if there is a problem in the appeal. Fields: group, topic, text.

Problem indicators: complaint, "не чистят", "не проехать", "нет воды", "нет отопления", accident, outage.
Not a problem: gratitude, question (without complaint), simple information.

Severity:
1 - no problem
2 - minor inconvenience
3 - group problem
4 - serious
5 - critical

IMPORTANT: problem_tags MUST be in RUSSIAN language.

Return JSON:
[{{"incident_id": ID, "is_problem": 0/1, "severity": 1-5, "problem_tags": ["tag1", "tag2"]}}]

Data:
{json.dumps(llm_input, ensure_ascii=False)}"""
    
    print("Отправляем запрос в LLM...")
    response = generate(prompt)
    print("Ответ получен")

    json_match = re.search(r'\[\s*\{.*?\}\s*\]', response, re.DOTALL)
    
    if json_match:
        json_str = json_match.group()
        try:
            results = json.loads(json_str)
            
            for result in results:
                if result.get('severity', 1) >= 2 and result.get('is_problem') == 0:
                    result['is_problem'] = 1
                if result.get('is_problem') == 0:
                    result['problem_tags'] = []
                if 'severity' not in result:
                    result['severity'] = 1
                if 'incident_id' not in result:
                    result['incident_id'] = 0
            
            return results
        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON: {e}")
            return []
    else:
        print(f"JSON не найден в ответе")
        return []