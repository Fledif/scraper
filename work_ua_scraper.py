import sqlite3
import requests
from bs4 import BeautifulSoup
import logging

# Налаштування виведення
logging.basicConfig(level=logging.INFO, format='%(message)s')

DB_NAME = 'career_engine.db'
URL = 'https://www.work.ua/jobs-kyiv/'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'uk,en-US;q=0.9,en;q=0.8'
}

def scrape_work_ua():
    logging.info(f"Завантаження сторінки: {URL}")
    try:
        response = requests.get(URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Помилка при завантаженні сторінки: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Знаходимо всі картки вакансій
    # На Work.ua картки зазвичай мають клас 'card' та 'card-hover' або 'job-link'
    job_cards = soup.find_all('div', class_=lambda x: x and 'card' in x.split() and ('card-hover' in x.split() or 'job-link' in x.split()))
    
    if not job_cards:
        logging.info("Не знайдено карток вакансій. Можливо, змінилася верстка сайту.")
        return

    logging.info(f"Знайдено вакансій на сторінці: {len(job_cards)}")
    
    parsed_jobs = []
    
    for card in job_cards:
        # Назва вакансії та URL
        title_element = card.find('h2')
        if not title_element:
            continue
            
        a_tag = title_element.find('a')
        if not a_tag:
            continue
            
        title = a_tag.text.strip()
        job_url = "https://www.work.ua" + a_tag.get('href', '')
        
        # Назва компанії
        company = "Не вказано"
        # Часто компанія знаходиться в span, що йде після логотипу або має певні класи
        company_img = card.find('img', alt=True)
        if company_img and 'логотип' not in company_img['alt'].lower():
            company = company_img['alt']
        else:
            # Спроба знайти назву тексту, зазвичай це перший span зі шрифтом
            spans = card.find_all('span')
            for span in spans:
                if span.find_parent('h2') is None and span.text.strip():
                    company = span.text.strip()
                    break

        # Зарплата
        salary = "Не вказана"
        salary_elements = card.find_all('b')
        for el in salary_elements:
            if 'грн' in el.text or any(char.isdigit() for char in el.text) and '₴' in el.text:
                salary = el.text.strip().replace('\u202f', ' ').replace('\u200b', '')
                break
            
        # Короткий опис
        description = ""
        desc_element = card.find('p')
        if desc_element:
            description = desc_element.text.strip().replace('\n', ' ')

        parsed_jobs.append({
            'title': title,
            'company': company,
            'description': description,
            'salary': salary,
            'source': 'work_ua',
            'url': job_url
        })
        
    save_to_database(parsed_jobs)

def save_to_database(jobs):
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
                job['title'], 
                job['company'], 
                job['description'], 
                job['salary'], 
                job['source'], 
                job['url']
            ))
            
            # Якщо rowcount > 0, рядок був успішно доданий (не проігнорований через UNIQUE)
            if cursor.rowcount > 0:
                inserted_count += 1
                
        conn.commit()
        logging.info(f"Успішно додано в базу нових вакансій: {inserted_count}")
        
    except sqlite3.Error as e:
        logging.error(f"Помилка при збереженні в БД: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    scrape_work_ua()
