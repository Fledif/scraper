from fastapi import FastAPI, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import sqlite3
import asyncio
import json
from datetime import datetime, timedelta
from live_scraper import get_live_jobs

app = FastAPI()
templates = Jinja2Templates(directory="templates")
DB_NAME = "career_engine.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# Ініціалізація таблиці кешу при старті
with get_db_connection() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS search_cache (
            query TEXT PRIMARY KEY,
            results TEXT,
            cached_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, q: str = Query(None)):
    if q:
        q_lower = q.lower().strip()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Перевіряємо, чи є свіжий кеш (за останню 1 годину)
        one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            SELECT results FROM search_cache 
            WHERE query = ? AND cached_at >= ?
        """, (q_lower, one_hour_ago))
        row = cursor.fetchone()
        
        if row:
            # Якщо є кеш, миттєво віддаємо його
            all_jobs = json.loads(row['results'])
            conn.close()
        else:
            conn.close()
            # Кешу немає або він застарів – запускаємо живий пошук
            all_jobs = await get_live_jobs(q)
            
            # AI Processing for the top 15 jobs
            from ai_processor import process_vacancy_with_ai
            tasks = []
            for job in all_jobs[:15]:
                tasks.append(process_vacancy_with_ai(job.get('title', ''), "", job.get('salary', '')))
            
            ai_results = await asyncio.gather(*tasks)
            for i, job in enumerate(all_jobs[:15]):
                job.update(ai_results[i])
            
            # Зберігаємо новий результат у кеш
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO search_cache (query, results, cached_at) 
                VALUES (?, ?, ?)
            """, (q_lower, json.dumps(all_jobs), datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            conn.close()
    else:
        # Якщо пошукового запиту немає, просто віддаємо останні 50 вакансій з бази для головної сторінки
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, company, description, salary, source, url 
            FROM jobs 
            ORDER BY id DESC LIMIT 50
        """)
        all_jobs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"jobs": all_jobs, "query": q}
    )
