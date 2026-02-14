# Використовуємо образ, який вже має частину залежностей
FROM python:3.11-bullseye

# Оновлюємо та встановлюємо тільки необхідні системні бібліотеки
RUN apt-get update --fix-missing && apt-get install -y \
    wget \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Встановлюємо робочу директорію
WORKDIR /app

# Спочатку копіюємо вимоги, щоб кешувати встановлення бібліотек
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо решту проекту
COPY . .

# Встановлюємо Playwright та ВСІ його залежності автоматично
# Ця команда сама знає, які бібліотеки потрібні для системи
RUN playwright install chromium
RUN playwright install-deps chromium

# Запуск Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=10000", "--server.address=0.0.0.0"]
