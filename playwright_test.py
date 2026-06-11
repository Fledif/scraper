import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import aiosqlite
from bs4 import BeautifulSoup
import random
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_NAME = 'career_engine.db'

async def save_to_database(jobs):
    if not jobs: return
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            query = """
            INSERT OR IGNORE INTO jobs (title, company, description, salary, source, url)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            data = [
                (
                    job.get('title', ''), job.get('company', ''), job.get('description', ''), 
                    job.get('salary', ''), job.get('source', ''), job.get('url', '')
                ) for job in jobs
            ]
            cursor = await db.executemany(query, data)
            await db.commit()
            if cursor.rowcount > 0:
                logging.info(f"[DB] Збережено нових вакансій: {cursor.rowcount}")
    except Exception as e:
        logging.error(f"[DB] Помилка: {e}")

async def scrape_with_playwright(browser, site_name, url_template, page_handler, max_pages):
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080}
    )
    page_context = await context.new_page()
    await Stealth().apply_stealth_async(page_context)

    logging.info(f"[{site_name}] Починаємо скрапінг...")
    
    for page_num in range(1, max_pages + 1):
        url = url_template(page_num)
        try:
            await page_context.goto(url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(random.uniform(2.0, 4.0))
            
            if site_name == "Robota.ua":
                try:
                    await page_context.wait_for_selector("article, div[class*='santa-']", timeout=5000)
                except:
                    pass
                    
            if site_name == "Jooble":
                try:
                    await page_context.wait_for_selector("article, div[data-test-id='vacancy-card']", timeout=5000)
                except:
                    pass

            html = await page_context.content()
            count = await page_handler(html, page_num)
            
            if count == 0:
                logging.info(f"[{site_name}] На сторінці {page_num} не знайдено вакансій. Можливо, блок або кінець.")
                break
                
            logging.info(f"[{site_name}] Сторінка {page_num}: Зібрано {count} вакансій.")
            
        except Exception as e:
            logging.error(f"[{site_name}] Помилка на сторінці {page_num}: {e}")
            break

    await context.close()

# --- HANDLERS ---
async def handle_jooble(html, page_num):
    soup = BeautifulSoup(html, 'html.parser')
    cards = soup.find_all('article') or soup.find_all('div', attrs={"data-test-id": "vacancy-card"})
    if not cards: return 0

    jobs = []
    for card in cards:
        title_tag = card.find('h2') or card.find('a')
        if not title_tag: continue
        a_tag = title_tag if title_tag.name == 'a' else title_tag.find('a')
        if not a_tag: continue
        title = a_tag.text.strip()
        href = a_tag.get('href', '')
        job_url = f"https://ua.jooble.org{href}" if href.startswith('/') else href
        
        company_tag = card.find('p', class_=lambda x: x and 'company' in x.lower()) or card.find('div', class_=lambda x: x and 'company' in x.lower())
        company = company_tag.text.strip() if company_tag else 'Не вказано'
        
        salary_tag = card.find('p', class_=lambda x: x and 'salary' in x.lower())
        salary = salary_tag.text.strip() if salary_tag else 'Не вказана'
        
        desc_tag = card.find('div', class_=lambda x: x and 'desc' in x.lower())
        desc = desc_tag.text.strip() if desc_tag else ''
        
        if title and job_url:
            jobs.append({'title': title, 'company': company, 'description': desc, 'salary': salary, 'source': 'jooble', 'url': job_url})
    
    await save_to_database(jobs)
    return len(jobs)

async def handle_robota(html, page_num):
    soup = BeautifulSoup(html, 'html.parser')
    cards = soup.find_all('article')
    if not cards:
        cards = soup.find_all('div', class_=lambda x: x and 'santa-' in x)
        cards = [c for c in cards if c.find('a') and c.find('h2')]
    if not cards: return 0
        
    jobs = []
    for card in cards:
        a_tag = card.find('a')
        if not a_tag: continue
        title_tag = card.find('h2') or card.find('h3')
        title = title_tag.text.strip() if title_tag else a_tag.text.strip()
        href = a_tag.get('href', '')
        job_url = f"https://robota.ua{href}" if href.startswith('/') else href
        
        company = 'Не вказано'
        company_tag = card.find('span', class_=lambda x: x and ('company' in x.lower() or 'employer' in x.lower()))
        if not company_tag: company_tag = card.find('a', href=lambda x: x and '/company' in x.lower())
        if company_tag: company = company_tag.text.strip()
        
        salary = 'Не вказана'
        salary_tag = card.find('span', class_=lambda x: x and ('salary' in x.lower() or 'price' in x.lower()))
        if salary_tag: salary = salary_tag.text.strip()
        
        desc_tag = card.find('div', class_=lambda x: x and 'description' in x.lower())
        desc = desc_tag.text.strip() if desc_tag else ''
        
        if title and job_url and '/company' not in job_url:
            jobs.append({'title': title, 'company': company, 'description': desc, 'salary': salary, 'source': 'robota_ua', 'url': job_url})
            
    await save_to_database(jobs)
    return len(jobs)

async def main():
    MAX_PAGES = 2 
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        tasks = [
            scrape_with_playwright(browser, "Jooble", lambda p: f"https://ua.jooble.org/SearchResult?p={p}", handle_jooble, MAX_PAGES),
            scrape_with_playwright(browser, "Robota.ua", lambda p: f"https://robota.ua/zapros/ukraine?page={p}", handle_robota, MAX_PAGES)
        ]
        await asyncio.gather(*tasks)
        await browser.close()
        logging.info("Тест Playwright завершено!")

if __name__ == "__main__":
    # Use default event loop policy
    asyncio.run(main())
