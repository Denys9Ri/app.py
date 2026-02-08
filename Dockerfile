FROM python:3.11-slim

# Встановлюємо системні залежності
RUN apt-get update && apt-get install -y \
    curl \
    bash \
    git \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Встановлюємо OpenClaw (додаємо --yes для повної автоматизації)
RUN curl -fsSL https://openclaw.ai/install.sh | bash -s -- --yes

# Додаємо шлях до OpenClaw в систему
ENV PATH="/root/.openclaw/bin:${PATH}"

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

# Render використовує змінну оточення PORT, тому важливо її вказати
EXPOSE 10000

CMD ["streamlit", "run", "app.py", "--server.port", "10000", "--server.address", "0.0.0.0"]

