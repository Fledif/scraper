import asyncio
from bs4 import BeautifulSoup
from curl_cffi.requests import AsyncSession
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import urllib.parse
import logging

logging.basicConfig(level=logging.INFO)

playwright_semaphore = asyncio.Semaphore(1)

async def fetch_with_playwright(url, source_name, wait_selector=None):
    async with playwright_semaphore:
        print(f"[{source_name}] Блок Cloudflare! Запускаю Playwright Fallback...")
        html = None
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080}
                )
                page = await context.new_page()
                await Stealth().apply_stealth_async(page)
                
                await page.goto(url, timeout=10000)
                if wait_selector:
                    try:
                        await page.wait_for_selector(wait_selector, timeout=10000)
                    except:
                        print(f"[{source_name}] Playwright: timeout waiting for selector {wait_selector}")
                else:
                    await asyncio.sleep(3) 
                    
                html = await page.content()
                await browser.close()
        except Exception as e:
            print(f"[{source_name}] Playwright error: {e}")
        return html

async def fetch_page_curl(base_url, search_url):
    async with AsyncSession(impersonate="chrome120") as session:
        await session.get(base_url, timeout=5)
        res = await session.get(search_url, timeout=5)
        
        lower_text = res.text.lower()
        # Прибрали занадто жорстку перевірку на слово cloudflare, залишили реальні індикатори блокування
        if res.status_code in [403, 503] or "just a moment" in lower_text or "checking your browser" in lower_text:
            raise ValueError("Cloudflare block detected (status or text)")
            
        return res.text

# === PARSERS ===

async def scrape_work_live(query):
    if not query: return []
    formatted_query = query.strip().replace(' ', '+')
    base_url = "https://www.work.ua/"
    search_url = f"https://www.work.ua/jobs-{formatted_query}/"
    
    try:
        html = await fetch_page_curl(base_url, search_url)
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.find_all('div', class_=lambda x: x and 'card' in x and 'job-link' in x)
        
        if not cards:
            raise ValueError("Empty content")
            
    except Exception as e:
        html = await fetch_with_playwright(search_url, "Work.ua", wait_selector="div.job-link")
        if not html: return []
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.find_all('div', class_=lambda x: x and 'card' in x and 'job-link' in x)

    jobs = []
    for card in cards[:20]:
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
        
        jobs.append({'title': title, 'company': company, 'url': job_url, 'salary': salary, 'source': 'Work.ua'})
    return jobs

async def scrape_jobs_live(query):
    if not query: return []
    encoded_query = urllib.parse.quote(query)
    base_url = "https://jobs.ua/"
    search_url = f"https://jobs.ua/vacancy/search?q={encoded_query}"
    
    try:
        html = await fetch_page_curl(base_url, search_url)
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.find_all('li', class_='b-vacancy__item')
        if not cards:
            raise ValueError("Empty content")
    except Exception as e:
        html = await fetch_with_playwright(search_url, "Jobs.ua", wait_selector="li.b-vacancy__item")
        if not html: return []
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.find_all('li', class_='b-vacancy__item')

    jobs = []
    for card in cards[:20]:
        a_tag = card.find('a', class_='b-vacancy__top__title')
        if not a_tag: continue
        
        title = a_tag.text.strip()
        href = a_tag.get('href', '')
        job_url = href if href.startswith('http') else f"https://www.jobs.ua{href}"
        
        company_tag = card.find('span', class_='b-vacancy__tech__item')
        company = company_tag.text.strip() if company_tag else 'Не вказано'
        salary_tag = card.find('span', class_='b-vacancy__top__pay')
        salary = salary_tag.text.strip() if salary_tag else 'Не вказана'
        
        jobs.append({'title': title, 'company': company, 'url': job_url, 'salary': salary, 'source': 'Jobs.ua'})
    return jobs

async def scrape_jooble_live(query):
    if not query: return []
    encoded_query = urllib.parse.quote(query)
    base_url = "https://ua.jooble.org/"
    search_url = f"https://ua.jooble.org/SearchResult?ukw={encoded_query}"
    
    try:
        html = await fetch_page_curl(base_url, search_url)
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.find_all('article') or soup.find_all('div', attrs={"data-test-id": "vacancy-card"})
        if not cards:
            raise ValueError("Empty content")
    except Exception as e:
        html = await fetch_with_playwright(search_url, "Jooble", wait_selector="article, [data-test-id='vacancy-card']")
        if not html: return []
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.find_all('article') or soup.find_all('div', attrs={"data-test-id": "vacancy-card"})

    jobs = []
    for card in cards[:20]:
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
        
        jobs.append({'title': title, 'company': company, 'url': job_url, 'salary': salary, 'source': 'Jooble'})
    return jobs

async def scrape_robota_live(query):
    if not query: return []
    encoded_query = urllib.parse.quote(query)
    base_url = "https://robota.ua/"
    search_url = f"https://robota.ua/zapros/{encoded_query}"
    
    try:
        html = await fetch_page_curl(base_url, search_url)
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.find_all('article')
        if not cards:
            cards = soup.find_all('div', class_=lambda x: x and 'santa-' in x)
            cards = [c for c in cards if c.find('a') and c.find('h2')]
        if not cards:
            raise ValueError("Empty content")
    except Exception as e:
        html = await fetch_with_playwright(search_url, "Robota.ua", wait_selector="article, div[class*='santa-']")
        if not html: return []
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.find_all('article')
        if not cards:
            cards = soup.find_all('div', class_=lambda x: x and 'santa-' in x)
            cards = [c for c in cards if c.find('a') and c.find('h2')]

    jobs = []
    for card in cards[:20]:
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
        
        if '/company' not in job_url:
            jobs.append({'title': title, 'company': company, 'url': job_url, 'salary': salary, 'source': 'Robota.ua'})
    return jobs

async def safe_scrape(task_coro, timeout=25.0):
    try:
        # Збільшено до 25 сек, бо Playwright з JS-challenge може тривати до 15 сек
        return await asyncio.wait_for(task_coro, timeout=timeout)
    except asyncio.TimeoutError:
        print("⏳ Скрапер не встиг за визначений час (таймаут).")
        return []
    except Exception as e:
        print(f"❌ Помилка скрапера: {e}")
        return []

async def get_live_jobs(query):
    if not query:
        return []
    
    tasks = [
        safe_scrape(scrape_work_live(query)),
        safe_scrape(scrape_jobs_live(query)),
        safe_scrape(scrape_jooble_live(query)),
        safe_scrape(scrape_robota_live(query))
    ]
    
    results = await asyncio.gather(*tasks)
    
    live_jobs = []
    for r in results:
        live_jobs.extend(r)
        
    return live_jobs
