FROM python:3.11-slim

# Встановлюємо необхідні системні інструменти
RUN apt-get update && apt-get install -y curl bash git nodejs npm

# Встановлюємо OpenClaw автоматично
RUN curl -fsSL https://openclaw.ai/install.sh | bash -s -- --yes

# Додаємо шлях до PATH
ENV PATH="/root/.openclaw/bin:/opt/render/project/nodes/node-22.22.0/bin:${PATH}"

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

# Запуск
CMD ["streamlit", "run", "app.py", "--server.port", "10000"]
