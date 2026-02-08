FROM python:3.11-slim

# Налаштування середовища
ENV DEBIAN_FRONTEND=noninteractive
ENV NODE_MAJOR=20

# Встановлюємо системні пакети та Node.js
RUN apt-get update && apt-get install -y \
    curl \
    bash \
    git \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_$NODE_MAJOR.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Встановлюємо OpenClaw глобально через npm
RUN npm install -g openclaw

# Додаємо шлях до глобальних бінарників npm у PATH
ENV PATH="/usr/local/bin:$PATH"

WORKDIR /app
COPY . .

# Встановлюємо залежності Python (включаючи langchain та openai)
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 10000

# Запуск
CMD ["streamlit", "run", "app.py", "--server.port", "10000", "--server.address", "0.0.0.0"]


