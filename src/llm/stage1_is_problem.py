import json
from src.llm.llama_client import generate

def classify_is_problem(batch):
    
    llm_input = []
    for row in batch:
        llm_input.append({
            "incident_id": row["incident_id"],
            "text": str(row.get("Текст инцидента", ""))
        })
    
    prompt = """Ты классификатор обращений граждан. Определи, является ли обращение ПРОБЛЕМОЙ.

ПРИМЕРЫ:

Пример 1 (ПРОБЛЕМА):
Текст: "Вторую неделю нет отопления в квартире, батареи холодные."
Ответ: {"is_problem": 1}

Пример 2 (НЕ ПРОБЛЕМА - вопрос):
Текст: "Подскажите, пожалуйста, во сколько начнутся соревнования?"
Ответ: {"is_problem": 0}

Пример 3 (НЕ ПРОБЛЕМА - благодарность):
Текст: "Спасибо большое за чистые дороги и парки!"
Ответ: {"is_problem": 0}

Пример 4 (ПРОБЛЕМА - сарказм):
Текст: "Спасибо, что снег не чистите, очень удобно по сугробам ходить"
Ответ: {"is_problem": 1}

Пример 5 (ПРОБЛЕМА - яма на дороге):
Текст: "На улице Ленина огромная яма, сломали колесо, просим отремонтировать"
Ответ: {"is_problem": 1}

Пример 6 (НЕ ПРОБЛЕМА - информация):
Текст: "Сообщаю, что завтра с 10:00 до 18:00 будет отключена горячая вода по адресу..."
Ответ: {"is_problem": 0}

ПРАВИЛА:
- 1 = проблема (жалоба, авария, отключение, сарказм, просьба решить)
- 0 = не проблема (вопрос, благодарность, информация)

ТЕПЕРЬ ОПРЕДЕЛИ ДЛЯ СЛЕДУЮЩИХ ОБРАЩЕНИЙ. Верни ТОЛЬКО JSON-массив:

[{"incident_id": ID, "is_problem": 0/1}]

Данные:
""" + json.dumps(llm_input, ensure_ascii=False)

    print("  [Этап 1] Определяем is_problem...")
    response = generate(prompt).strip()
    
    if response.startswith("```json"):
        response = response.split("```json")[1].split("```")[0].strip()
    elif response.startswith("```"):
        response = response.split("```")[1].split("```")[0].strip()
    
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        print(f"    Ошибка парсинга JSON: {e}")
        print(f"    Ответ: {response[:200]}")
        fallback_results = []
        for row in batch:
            text = str(row.get("Текст инцидента", "")).lower()
            is_problem = 1 if any(kw in text for kw in ["не чист", "нет воды", "нет отопления", "яма", "авария", "отключили"]) else 0
            fallback_results.append({"incident_id": row["incident_id"], "is_problem": is_problem})
        return fallback_results