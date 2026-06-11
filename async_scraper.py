import asyncio
import aiosqlite
from bs4 import BeautifulSoup
import logging
from proxy_manager import ProxyManager
from curl_cffi.requests import AsyncSession
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DB_NAME = 'career_engine.db'
MAX_PAGES = 2500 # 2500 сторінок * ~20 вакансій = ~50,000

proxy_pool = []

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                company TEXT,
                description TEXT,
                salary TEXT,
                source TEXT,
                url TEXT UNIQUE
            )
        ''')
        await db.commit()

async def save_to_db(jobs):
    if not jobs: return
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            query = """
            INSERT OR IGNORE INTO jobs (title, company, description, salary, source, url)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            data = [(
                j.get('title',''), j.get('company',''), j.get('description',''), 
                j.get('salary',''), j.get('source',''), j.get('url','')
            ) for j in jobs]
            cursor = await db.executemany(query, data)
            await db.commit()
            if cursor.rowcount > 0:
                logging.info(f"[DB] Додано {cursor.rowcount} нових вакансій.")
    except Exception as e:
        logging.error(f"[DB] Помилка: {e}")

async def fetch_page(url, use_proxy=False, max_retries=3):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    for attempt in range(max_retries):
        proxies = None
        if use_proxy and proxy_pool:
            proxy = random.choice(proxy_pool)
            proxies = {"http": proxy, "https": proxy}
            
        try:
            async with AsyncSession(proxies=proxies, impersonate="chrome110") as session:
                res = await session.get(url, timeout=15)
                if res.status_code == 200 and "Just a moment" not in res.text:
                    return res.text
                if res.status_code == 404:
                    return None
        except Exception as e:
            pass
        await asyncio.sleep(2)
    return None

# --- PARSERS ---
async def scrape_work_ua():
    for p in range(1, MAX_PAGES + 1):
        url = f"https://www.work.ua/jobs/?page={p}"
        html = await fetch_page(url)
        if not html: break
        
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.find_all('div', class_=lambda x: x and 'card' in x and 'job-link' in x)
        if not cards: break
            
        jobs = []
        for card in cards:
            title_tag = card.find('h2')
            if not title_tag: continue
            a_tag = title_tag.find('a')
            if not a_tag: continue
            
            title = a_tag.get('title', a_tag.text).strip()
            href = a_tag.get('href', '')
            job_url = f"https://www.work.ua{href}"
            
            company_tag = card.find('div', class_='add-top-xs')
            company = company_tag.find('span').text.strip() if company_tag and company_tag.find('span') else 'Не вказано'
            
            salary_tag = card.find('b')
            salary = salary_tag.text.strip() if salary_tag else 'Не вказана'
            
            desc_tag = card.find('p', class_='overflow')
            desc = desc_tag.text.strip() if desc_tag else ''
            
            jobs.append({'title': title, 'company': company, 'description': desc, 'salary': salary, 'source': 'work_ua', 'url': job_url})
            
        await save_to_db(jobs)
        logging.info(f"[Work.ua] Сторінка {p}: {len(jobs)} вакансій")
        await asyncio.sleep(1)

async def scrape_jobs_ua():
    for p in range(1, MAX_PAGES + 1):
        url = f"https://www.jobs.ua/ukr/vacancy/page-{p}"
        html = await fetch_page(url)
        if not html: break
        
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.find_all('li', class_='b-vacancy__item')
        if not cards: break
            
        jobs = []
        for card in cards:
            a_tag = card.find('a', class_='b-vacancy__top__title')
            if not a_tag: continue
            
            title = a_tag.text.strip()
            href = a_tag.get('href', '')
            job_url = href if href.startswith('http') else f"https://www.jobs.ua{href}"
            
            company_tag = card.find('span', class_='b-vacancy__tech__item')
            company = company_tag.text.strip() if company_tag else 'Не вказано'
            
            salary_tag = card.find('span', class_='b-vacancy__top__pay')
            salary = salary_tag.text.strip() if salary_tag else 'Не вказана'
            
            desc_tag = card.find('div', class_='b-vacancy__bottom')
            desc = desc_tag.text.strip() if desc_tag else ''
            
            jobs.append({'title': title, 'company': company, 'description': desc, 'salary': salary, 'source': 'jobs_ua', 'url': job_url})
            
        await save_to_db(jobs)
        logging.info(f"[Jobs.ua] Сторінка {p}: {len(jobs)} вакансій")
        await asyncio.sleep(1)

async def scrape_jooble():
    for p in range(1, MAX_PAGES + 1):
        url = f"https://ua.jooble.org/SearchResult?p={p}"
        html = await fetch_page(url, use_proxy=True)
        if not html: 
            logging.warning(f"[Jooble] Сторінка {p} не завантажилась (можливо бан).")
            continue
            
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.find_all('article') or soup.find_all('div', attrs={"data-test-id": "vacancy-card"})
        if not cards: break
            
        jobs = []
        for card in cards:
            title_tag = card.find('h2') or card.find('a')
            if not title_tag: continue
            a_tag = title_tag if title_tag.name == 'a' else title_tag.find('a')
            if not a_tag: continue
            
            title = a_tag.text.strip()
            href = a_tag.get('href', '')
            job_url = f"https://ua.jooble.org{href}" if href.startswith('/') else href
            
            company_tag = card.find('p', class_=lambda x: x and 'company' in x.lower())
            company = company_tag.text.strip() if company_tag else 'Не вказано'
            salary_tag = card.find('p', class_=lambda x: x and 'salary' in x.lower())
            salary = salary_tag.text.strip() if salary_tag else 'Не вказана'
            desc_tag = card.find('div', class_=lambda x: x and 'desc' in x.lower())
            desc = desc_tag.text.strip() if desc_tag else ''
            
            jobs.append({'title': title, 'company': company, 'description': desc, 'salary': salary, 'source': 'jooble', 'url': job_url})
            
        await save_to_db(jobs)
        logging.info(f"[Jooble] Сторінка {p}: {len(jobs)} вакансій")

async def scrape_robota():
    for p in range(1, MAX_PAGES + 1):
        url = f"https://robota.ua/zapros/ukraine?page={p}"
        html = await fetch_page(url, use_proxy=True)
        if not html: 
            logging.warning(f"[Robota.ua] Сторінка {p} не завантажилась.")
            continue
            
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.find_all('article')
        if not cards:
            cards = soup.find_all('div', class_=lambda x: x and 'santa-' in x)
            cards = [c for c in cards if c.find('a') and c.find('h2')]
        if not cards: break
            
        jobs = []
        for card in cards:
            a_tag = card.find('a')
            if not a_tag: continue
            title_tag = card.find('h2') or card.find('h3')
            title = title_tag.text.strip() if title_tag else a_tag.text.strip()
            href = a_tag.get('href', '')
            job_url = f"https://robota.ua{href}" if href.startswith('/') else href
            
            company_tag = card.find('span', class_=lambda x: x and ('company' in x.lower() or 'employer' in x.lower()))
            company = company_tag.text.strip() if company_tag else 'Не вказано'
            salary_tag = card.find('span', class_=lambda x: x and ('salary' in x.lower() or 'price' in x.lower()))
            salary = salary_tag.text.strip() if salary_tag else 'Не вказана'
            desc = ''
            
            if '/company' not in job_url:
                jobs.append({'title': title, 'company': company, 'description': desc, 'salary': salary, 'source': 'robota_ua', 'url': job_url})
                
        await save_to_db(jobs)
        logging.info(f"[Robota.ua] Сторінка {p}: {len(jobs)} вакансій")

async def main():
    await init_db()
    
    # Спочатку завантажимо кілька робочих проксі
    pm = ProxyManager()
    global proxy_pool
    proxy_pool = await pm.get_working_proxies(limit=5)
    
    if not proxy_pool:
        logging.warning("Робочих проксі не знайдено! Jooble та Robota можуть бути заблоковані.")
    
    # Обмеження одночасних задач
    sem = asyncio.Semaphore(15)
    async def run_with_sem(task):
        async with sem:
            await task()
            
    tasks = [
        run_with_sem(scrape_work_ua),
        run_with_sem(scrape_jobs_ua),
        run_with_sem(scrape_jooble),
        run_with_sem(scrape_robota)
    ]
    
    logging.info("🚀 Запуск скрапера для 50 000 вакансій...")
    await asyncio.gather(*tasks)
    logging.info("Скрапінг завершено!")

if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
