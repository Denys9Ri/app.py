FROM python:3.11-slim

# Системні залежності для браузерів
RUN apt-get update && apt-get install -y \
    curl bash git nodejs npm \
    libgbm-dev libnss3 libatk-bridge2.0-0 libgtk-3-0 libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Встановлюємо Python бібліотеки
RUN pip install --no-cache-dir -r requirements.txt

# Встановлюємо браузери Playwright
RUN playwright install chromium --with-deps

EXPOSE 10000

CMD ["streamlit", "run", "app.py", "--server.port", "10000", "--server.address", "0.0.0.0"]
