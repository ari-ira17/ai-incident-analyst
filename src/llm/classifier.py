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
            "text": str(row.get("Текст инцидента", ""))[:100]
        })
    
    prompt = f"""Анализ обращений. Поля: group, topic, text.

Severity:
1 - благодарность/вопрос/не проблема
2 - мелкое неудобство (мусор, трава, скамейки)
3 - проблема для групп (дороги, школы, транспорт)
4 - серьёзное (отключение воды/тепла, прорыв, больницы)
5 - критическое (угроза жизни, авария при морозе, отопление зимой)

Признаки проблемы: жалоба, "не чистят", "авария", "отключили", сарказм.

Пример правильного ответа для двух инцидентов:
[
  {{"incident_id": 123, "is_problem": 1, "severity": 3}},
  {{"incident_id": 124, "is_problem": 0, "severity": 1}}
]

Данные:
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
