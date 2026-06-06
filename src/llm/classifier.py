import json

from src.llm.llama_client import generate


def classify_batch(batch):

    llm_input = []

    for row in batch:

        llm_input.append({
            "incident_id": row["incident_id"],
            "group": str(row.get("Группа тем", "")),
            "topic": str(row.get("Тема", "")),
            "text": str(row.get("Текст инцидента", ""))
        })

    prompt = f"""
Ты аналитик муниципальных инцидентов.

Каждая запись содержит:

group - группа тем
topic - тема
text - текст обращения

Используй ВСЕ поля одновременно.

Определи:
1. is_problem
0 - проблема отсутствует
1 - проблема присутствует

2. severity
1 - благодарность, предложение или отсутствие проблемы
2 - локальное неудобство
3 - проблема для группы жителей
4 - серьёзное нарушение городской услуги
5 - критическая ситуация,
угроза жизни,
угроза здоровью,
либо массовое нарушение услуги

3. problem_tags
От 2 до 4 кратких тегов.
Каждый тег:
- от 2 до 6 слов
- отражает конкретную проблему
Примеры хороших тегов:
нет отопления
авария на теплотрассе
не работает светофор
нехватка мест в школе
нет продленки для первого класса

Верни ТОЛЬКО JSON.
Формат ответа:

[
  {{
    "incident_id": 1,
    "is_problem": 1,
    "severity": 4,
    "problem_tags": [
      "нет отопления",
      "авария на теплотрассе"
    ]
  }}
]

Данные:

{json.dumps(llm_input, ensure_ascii=False)}
"""

    print("Отправляем запрос в LLM...")
    response = generate(prompt)
    print("Ответ получен")

    print("Сырой ответ LLM:")
    print(response[:500])

    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        print(f"Ошибка парсинга JSON: {e}")
        print("Первые 200 символов ответа:", response[:200])
        raise
