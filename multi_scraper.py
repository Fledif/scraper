import sqlite3
import requests
from bs4 import BeautifulSoup
import logging
import time
import random

logging.basicConfig(level=logging.INFO, format='%(message)s')

DB_NAME = 'career_engine.db'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'uk,en-US;q=0.9,en;q=0.8'
}

def save_to_database(jobs):
    if not jobs:
        return
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        inserted_count = 0
        for job in jobs:
            query = """
            INSERT OR IGNORE INTO jobs (title, company, description, salary, source, url)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            cursor.execute(query, (
                job.get('title', ''), 
                job.get('company', ''), 
                job.get('description', ''), 
                job.get('salary', ''), 
                job.get('source', ''), 
                job.get('url', '')
            ))
            if cursor.rowcount > 0:
                inserted_count += 1
        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Помилка БД: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def scrape_robota_ua():
    source = 'robota_ua'
    url = 'https://robota.ua/zapros/kyiv'
    jobs = []
    try:
        time.sleep(random.uniform(1, 2))
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        cards = soup.find_all('article')
        if not cards:
            cards = soup.find_all('div', class_=lambda x: x and 'santa-' in x)
            cards = [c for c in cards if c.find('a') and c.find('h2')]
            
        for card in cards:
            a_tag = card.find('a')
            if not a_tag:
                continue
                
            title_tag = card.find('h2') or card.find('h3')
            title = title_tag.text.strip() if title_tag else a_tag.text.strip()
            
            href = a_tag.get('href', '')
            job_url = f"https://robota.ua{href}" if href.startswith('/') else href
            
            company = 'Не вказано'
            company_tag = card.find('span', class_=lambda x: x and ('company' in x.lower() or 'employer' in x.lower()))
            if not company_tag:
                company_tag = card.find('a', href=lambda x: x and '/company' in x.lower())
            if company_tag:
                company = company_tag.text.strip()
            
            salary = 'Не вказана'
            salary_tag = card.find('span', class_=lambda x: x and ('salary' in x.lower() or 'price' in x.lower()))
            if salary_tag:
                salary = salary_tag.text.strip()
            
            desc = ''
            desc_tag = card.find('div', class_=lambda x: x and 'description' in x.lower())
            if desc_tag:
                desc = desc_tag.text.strip()
            
            if title and job_url and '/company' not in job_url:
                jobs.append({
                    'title': title, 'company': company, 'description': desc, 
                    'salary': salary, 'source': source, 'url': job_url
                })
        
        save_to_database(jobs)
        logging.info(f"[Robota.ua] скрапнуто: знайдено {len(jobs)} вакансій")
    except Exception as e:
        logging.error(f"[Robota.ua] Помилка: {e}")

def scrape_jooble():
    source = 'jooble'
    url = 'https://ua.jooble.org/work-kyiv'
    jobs = []
    try:
        time.sleep(random.uniform(1, 2))
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        cards = soup.find_all('article') or soup.find_all('div', attrs={"data-test-id": "vacancy-card"})
        for card in cards:
            title_tag = card.find('h2') or card.find('a')
            if not title_tag:
                continue
            
            a_tag = title_tag if title_tag.name == 'a' else title_tag.find('a')
            if not a_tag:
                continue
                
            title = a_tag.text.strip()
            href = a_tag.get('href', '')
            job_url = f"https://ua.jooble.org{href}" if href.startswith('/') else href
            
            company = 'Не вказано'
            company_tag = card.find('p', class_=lambda x: x and 'company' in x.lower()) or card.find('div', class_=lambda x: x and 'company' in x.lower())
            if company_tag:
                company = company_tag.text.strip()
            
            salary = 'Не вказана'
            salary_tag = card.find('p', class_=lambda x: x and 'salary' in x.lower())
            if salary_tag:
                salary = salary_tag.text.strip()
            
            desc = ''
            desc_tag = card.find('div', class_=lambda x: x and 'desc' in x.lower())
            if desc_tag:
                desc = desc_tag.text.strip()
            
            if title and job_url:
                jobs.append({
                    'title': title, 'company': company, 'description': desc, 
                    'salary': salary, 'source': source, 'url': job_url
                })
            
        save_to_database(jobs)
        logging.info(f"[Jooble] скрапнуто: знайдено {len(jobs)} вакансій")
    except Exception as e:
        logging.error(f"[Jooble] Помилка: {e}")

def scrape_happy_monday():
    source = 'happy_monday'
    url = 'https://happymonday.ua/jobs/'
    jobs = []
    try:
        time.sleep(random.uniform(1, 2))
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        cards = soup.find_all('div', class_=lambda x: x and 'job-card' in x) or soup.find_all('a', class_=lambda x: x and 'job-card' in x)
        if not cards:
             cards = soup.find_all('article')
             
        for card in cards:
            title_tag = card.find('h3') or card.find('h2')
            if not title_tag:
                continue
            title = title_tag.text.strip()
            
            a_tag = card if card.name == 'a' else card.find('a')
            if not a_tag:
                continue
            href = a_tag.get('href', '')
            job_url = f"https://happymonday.ua{href}" if href.startswith('/') else href
            
            company = 'Не вказано'
            company_tag = card.find('span', class_=lambda x: x and 'company' in x.lower()) or card.find('p', class_=lambda x: x and 'company' in x.lower())
            # For happymonday company is usually prominent
            if not company_tag:
                 company_tag = card.find('div', class_=lambda x: x and 'company' in x.lower())
            if company_tag:
                company = company_tag.text.strip()
            
            salary = 'Не вказана'
            
            desc = ''
            desc_tag = card.find('p', class_=lambda x: x and 'desc' in x.lower())
            if desc_tag:
                desc = desc_tag.text.strip()
            
            if title and job_url:
                jobs.append({
                    'title': title, 'company': company, 'description': desc, 
                    'salary': salary, 'source': source, 'url': job_url
                })
        
        save_to_database(jobs)
        logging.info(f"[Happy Monday] скрапнуто: знайдено {len(jobs)} вакансій")
    except Exception as e:
        logging.error(f"[Happy Monday] Помилка: {e}")

def scrape_jobs_ua():
    source = 'jobs_ua'
    url = 'https://www.jobs.ua/ukr/vacancy/kyiv'
    jobs = []
    try:
        time.sleep(random.uniform(1, 2))
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        cards = soup.find_all('li', class_=lambda x: x and 'vacancy' in x) or soup.find_all('div', class_=lambda x: x and 'vacancy' in x)
        if not cards:
             # fallback if structure is very simple
             cards = soup.find_all('div', class_='b-vacancy__item')
             
        for card in cards:
            title_tag = card.find('h2') or card.find('h3') or card.find('a', class_=lambda x: x and 'title' in x)
            if not title_tag:
                continue
            
            a_tag = title_tag if title_tag.name == 'a' else title_tag.find('a')
            if not a_tag:
                continue
                
            title = a_tag.text.strip()
            href = a_tag.get('href', '')
            job_url = f"https://www.jobs.ua{href}" if href.startswith('/') else href
            
            company = 'Не вказано'
            company_tag = card.find('span', class_=lambda x: x and 'company' in x) or card.find('b') or card.find('a', class_=lambda x: x and 'company' in x)
            if company_tag:
                company = company_tag.text.strip()
            
            salary = 'Не вказана'
            salary_tag = card.find('span', class_=lambda x: x and 'salary' in x) or card.find('div', class_=lambda x: x and 'salary' in x)
            if salary_tag:
                salary = salary_tag.text.strip()
            
            desc = ''
            desc_tag = card.find('div', class_=lambda x: x and 'desc' in x) or card.find('p')
            if desc_tag:
                desc = desc_tag.text.strip()
            
            if title and job_url:
                jobs.append({
                    'title': title, 'company': company, 'description': desc, 
                    'salary': salary, 'source': source, 'url': job_url
                })
            
        save_to_database(jobs)
        logging.info(f"[Jobs.ua] скрапнуто: знайдено {len(jobs)} вакансій")
    except Exception as e:
        logging.error(f"[Jobs.ua] Помилка: {e}")

def main():
    logging.info("Початок парсингу сайтів...")
    scrape_robota_ua()
    scrape_jooble()
    scrape_happy_monday()
    scrape_jobs_ua()
    logging.info("Парсинг завершено.")

if __name__ == "__main__":
    main()
