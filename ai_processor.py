import os
import json
import asyncio
import google.generativeai as genai

# API ключ потрібно додати у змінні оточення на Render
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Використовуємо семафор для AI, щоб не перевищити rate limits безкоштовного API
ai_semaphore = asyncio.Semaphore(5)

async def process_vacancy_with_ai(title, description, salary_raw):
    if not GEMINI_API_KEY:
        # Fallback якщо API ключа немає
        return {
            "level": "Не вказано",
            "skills": [],
            "work_format": "Не вказано",
            "salary_clean": salary_raw or "Не вказана"
        }
        
    prompt = f"""
    Проаналізуй наступну вакансію та поверни суворо JSON формат (без ```json, тільки сам об'єкт).
    
    Посада: {title}
    Опис (може бути пустим або неповним): {description}
    Зарплата (вказана на сайті): {salary_raw}
    
    Потрібно витягти:
    1. "level": Middle, Junior, Senior або "Не вказано"
    2. "skills": список (масив) знайдених технологій або важливих навичок. Не більше 5.
    3. "work_format": Remote, Office, Hybrid або "Не вказано"
    4. "salary_clean": нормалізована чиста цифра зарплати або діапазон. Якщо невідомо - "Не вказано".
    """
    
    async def call_gemini():
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = await asyncio.to_thread(model.generate_content, prompt)
        return response.text

    async with ai_semaphore:
        try:
            # Даємо таймаут на відповідь від AI (10 сек)
            text_response = await asyncio.wait_for(call_gemini(), timeout=10.0)
            clean_json = text_response.strip()
            if clean_json.startswith('```json'):
                clean_json = clean_json[7:]
            if clean_json.startswith('```'):
                clean_json = clean_json[3:]
            if clean_json.endswith('```'):
                clean_json = clean_json[:-3]
            clean_json = clean_json.strip()
            
            result = json.loads(clean_json)
            
            # Валідація полів
            return {
                "level": result.get("level", "Не вказано"),
                "skills": result.get("skills", []),
                "work_format": result.get("work_format", "Не вказано"),
                "salary_clean": result.get("salary_clean", salary_raw or "Не вказана")
            }
        except Exception as e:
            print(f"AI Error for '{title}': {e}")
            return {
                "level": "Не вказано",
                "skills": [],
                "work_format": "Не вказано",
                "salary_clean": salary_raw or "Не вказана"
            }
