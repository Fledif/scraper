import asyncio
import time
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import sys
from collections import Counter
from live_scraper import get_live_jobs

async def run_test():
    query = "QA Automation"
    print(f"Пошуковий запит: '{query}'\n")
    
    start_time = time.time()
    
    # Виконуємо пошук
    print("Виконуємо пошук (максимальний таймаут 8 сек)...")
    jobs = await get_live_jobs(query)
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Аналізуємо результати
    total_jobs = len(jobs)
    source_counts = Counter(job['source'] for job in jobs)
    
    # Виводимо статистику
    print("=" * 40)
    print("📋 РЕЗУЛЬТАТИ ТЕСТУВАННЯ")
    print("=" * 40)
    print(f"⏱ Загальний час виконання:  {elapsed_time:.2f} секунд")
    print(f"📊 Загальна к-сть вакансій: {total_jobs}")
    print("\n🏢 Кількість по джерелах:")
    print(f"   - Work.ua:    {source_counts.get('Work.ua', 0)}")
    print(f"   - Jobs.ua:    {source_counts.get('Jobs.ua', 0)}")
    print(f"   - Jooble:     {source_counts.get('Jooble', 0)}")
    print(f"   - Robota.ua:  {source_counts.get('Robota.ua', 0)}")
    print("-" * 40)
    
    # Виводимо перші 3 результати
    if jobs:
        print("\n🔍 Перші 3 результати:")
        print(json.dumps(jobs[:3], indent=4, ensure_ascii=False))
    else:
        print("\n❌ Жодної вакансії не знайдено.")

if __name__ == "__main__":
    # Для коректної роботи playwright на Windows
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_test())
