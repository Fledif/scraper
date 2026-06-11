FROM python:3.11-slim

# Встановлюємо робочу директорію
WORKDIR /app

# Копіюємо список залежностей та встановлюємо їх
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Встановлюємо системні залежності та браузери для Playwright
RUN playwright install chromium
RUN playwright install-deps

# Копіюємо весь код проекту в контейнер
COPY . .

# Команда для запуску FastAPI через uvicorn з використанням порту від Render
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
