import os
import json
import asyncio
import google.generativeai as genai

# API ключ потрібно додати у змінні оточення на Render
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

async def process_vacancies_batch(vacancies_list):
    if not GEMINI_API_KEY or not vacancies_list:
        # Fallback: повертаємо сирі вакансії
        return vacancies_list
        
    # Формуємо JSON-рядок із вхідних даних (передаємо тільки необхідне для зменшення токенів)
    slim_vacancies = []
    for v in vacancies_list:
        slim_vacancies.append({
            "title": v.get("title", ""),
            "company": v.get("company", ""),
            "salary": v.get("salary", ""),
            "source": v.get("source", ""),
            "url": v.get("url", "")
        })
        
    raw_data = json.dumps(slim_vacancies, ensure_ascii=False)
    
    prompt = f"""
    Проаналізуй цей список вакансій. Поверни СУВОРИЙ, валідний JSON-масив об'єктів (без markdown, без ```json).
    Кожен об'єкт у масиві — це оброблена вакансія.
    
    ОБОВ'ЯЗКОВО виконай дедуплікацію: якщо є однакові вакансії від однієї компанії (навіть з різних сайтів), 
    об'єднай їх в один об'єкт. У полі `source` перелічи джерела через кому (наприклад: "Work.ua, Jooble") або зроби масив рядків.
    
    Для кожної унікальної вакансії згенеруй такі поля та збережи оригінальні:
    - "title": оригінальна назва
    - "company": компанія
    - "url": посилання (якщо було кілька джерел, залиш одне будь-яке)
    - "source": джерела через кому (або масив джерел)
    - "salary": оригінальна зарплата
    - "level": Junior, Middle, Senior, Lead або "Не вказано"
    - "skills": масив (список) технологій та навичок
    - "work_format": Remote, Office, Hybrid або "Не вказано"
    - "salary_clean": нормалізована чиста цифра зарплати (діапазон) або "Не вказано"
    - "decision_score": число від 0 до 100 (оцінка привабливості: висока ЗП і адекватні вимоги = високий бал)
    - "decision_reason": одне коротке речення-порада українською (напр. "Чудовий варіант для старту").
    
    Сирі дані вакансій:
    {raw_data}
    """
    
    async def call_gemini():
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = await asyncio.to_thread(model.generate_content, prompt)
        return response.text

    try:
        # Даємо збільшений таймаут на відповідь від AI для batch-запиту (25 сек)
        text_response = await asyncio.wait_for(call_gemini(), timeout=25.0)
        clean_json = text_response.strip()
        if clean_json.startswith('```json'):
            clean_json = clean_json[7:]
        if clean_json.startswith('```'):
            clean_json = clean_json[3:]
        if clean_json.endswith('```'):
            clean_json = clean_json[:-3]
        clean_json = clean_json.strip()
        
        result_array = json.loads(clean_json)
        
        if isinstance(result_array, list):
            return result_array
        return vacancies_list
    except Exception as e:
        print(f"AI Batch Error: {e}")
        return vacancies_list
