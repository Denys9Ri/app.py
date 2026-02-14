# Використовуємо офіційний образ Python
FROM python:3.11-slim

# Встановлюємо системні залежності для браузера
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    librandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Робоча директорія
WORKDIR /app

# Копіюємо файли проекту
COPY . .

# Встановлюємо бібліотеки
RUN pip install --no-cache-dir -r requirements.txt

# Встановлюємо браузер Playwright
RUN playwright install chromium
RUN playwright install-deps chromium

# Запуск Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=10000", "--server.address=0.0.0.0"]
