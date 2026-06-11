import sqlite3
import os
import logging

# Налаштування логування для виведення інформації або помилок
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

DB_NAME = 'career_engine.db'

def create_database():
    """Створює базу даних та таблицю jobs, якщо вона не існує."""
    db_exists = os.path.exists(DB_NAME)
    
    try:
        # Підключення до бази даних (якщо файлу немає, він буде створений)
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # SQL-запит для створення таблиці jobs
        create_table_query = """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT,
            description TEXT,
            salary TEXT,
            source TEXT NOT NULL,
            url TEXT UNIQUE,
            scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        cursor.execute(create_table_query)
        conn.commit()
        
        if not db_exists:
            logging.info(f"Базу даних '{DB_NAME}' та таблицю 'jobs' успішно створено.")
        else:
            logging.info(f"База даних '{DB_NAME}' вже існує. Перевірено наявність таблиці 'jobs'.")
            
    except sqlite3.Error as e:
        logging.error(f"Помилка при роботі з SQLite: {e}")
    finally:
        # Завжди закриваємо з'єднання з базою даних
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    create_database()
