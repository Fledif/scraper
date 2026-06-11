from fastapi import FastAPI, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import sqlite3
import asyncio
from live_scraper import get_live_jobs

app = FastAPI()
templates = Jinja2Templates(directory="templates")
DB_NAME = "career_engine.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, q: str = Query(None)):
    if q:
        # Прямий "пошуковик" по сайтах
        all_jobs = await get_live_jobs(q)
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
