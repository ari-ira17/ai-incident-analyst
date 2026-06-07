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
    
    prompt = f"""Аналитик. По group, topic, text определи проблему.

    Правила severity (1-5):
    1 - спасибо, вопрос
    2 - мусор, освещение, шум
    3 - дороги, школы, садики, транспорт, льготы
    4 - отключение воды, отопления, газа, поликлиники
    5 - потоп, авария, угроза жизни

    Важно:
    - Если текст про школы, садики, нехватку мест, продленку, кружки, занятия - severity 3
    - Если про дороги, снег, ямы, реагенты, чистку улиц - severity 3
    - Жалоба на отсутствие продленки или платных занятий = проблема (is_problem=1)

    is_problem: 1 если жалоба, 0 если спасибо или вопрос без жалобы
    problem_tags: 2-4 коротких тега на русском

    Пример правильных тегов: "нехватка продленки", "нет платных занятий", "плохие дороги", "отключили воду"

    Формат: [{{"incident_id": ID, "is_problem": 0/1, "severity": 1-5, "problem_tags": ["тег1", "тег2"]}}]

    Данные: {json.dumps(llm_input, ensure_ascii=False)}"""

    print("Отправляем запрос в LLM...")
    response = generate(prompt)
    print("Ответ получен")

    json_match = re.search(r'\[\s*\{.*?\}\s*\]', response, re.DOTALL)
    
    if json_match:
        json_str = json_match.group()
        try:
            results = json.loads(json_str)
            
            for result in results:
                if 'problem_tags' not in result or not result['problem_tags']:
                    result['problem_tags'] = ["не указано"]
                if 'severity' not in result:
                    result['severity'] = 1
                if 'is_problem' not in result:
                    result['is_problem'] = 0
                if 'incident_id' not in result:
                    result['incident_id'] = 0
            
            return results
        except json.JSONDecodeError as e:
            print(f"Ошибка парсинга JSON: {e}")
            print(f"JSON: {json_str[:500]}")
            return []
    else:
        print(f"JSON не найден в ответе")
        print(f"Ответ: {response[:500]}")
        return []