import os
import json
import asyncio
import google.generativeai as genai
from pydantic import BaseModel
from typing import List

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class AICareerVacancy(BaseModel):
    title: str
    company: str
    url: str
    level: str
    skills: List[str]
    work_format: str
    salary_clean: str
    decision_score: int
    decision_reason: str
    source: List[str]

class AIVacancyList(BaseModel):
    vacancies: List[AICareerVacancy]

async def process_vacancies_batch(vacancies_list):
    if not GEMINI_API_KEY or not vacancies_list:
        return vacancies_list
        
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
    Проаналізуй цей список вакансій. Поверни СУВОРИЙ, валідний JSON.
    ОБОВ'ЯЗКОВО виконай дедуплікацію: якщо є однакові вакансії від однієї компанії (навіть з різних сайтів), 
    об'єднай їх в один об'єкт. У полі `source` перелічи джерела як масив рядків.
    
    Вказівки:
    - "title": оригінальна назва
    - "company": компанія
    - "url": посилання (якщо було кілька джерел, залиш одне будь-яке)
    - "level": Junior, Middle, Senior, Lead або "Не вказано"
    - "skills": масив (список) технологій
    - "work_format": Remote, Office, Hybrid або "Не вказано"
    - "salary_clean": нормалізована чиста цифра зарплати (діапазон) або "Не вказано"
    - "decision_score": число від 0 до 100 (оцінка привабливості: висока ЗП і адекватні вимоги = високий бал)
    - "decision_reason": одне коротке речення-порада українською
    
    Сирі дані вакансій:
    {raw_data}
    """
    
    async def call_gemini():
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = await asyncio.to_thread(
            model.generate_content,
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                response_schema=AIVacancyList
            )
        )
        return response.text

    try:
        text_response = await asyncio.wait_for(call_gemini(), timeout=25.0)
        parsed_data = AIVacancyList.model_validate_json(text_response)
        
        # Convert Pydantic models back to dict for the main pipeline
        return [v.model_dump() for v in parsed_data.vacancies]
        
    except Exception as e:
        print(f"AI Batch Error (Pydantic parsing): {e}")
        return vacancies_list
