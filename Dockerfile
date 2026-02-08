# Беремо базовий образ з Python
FROM python:3.11-slim

# Встановлюємо curl та bash
RUN apt-get update && apt-get install -y curl bash

# Запускаємо ту саму команду встановлення OpenClaw
RUN curl -fsSL https://openclaw.ai/install.sh | bash

# Копіюємо твій код агента
WORKDIR /app
COPY . .

# Встановлюємо бібліотеки для Python
RUN pip install -r requirements.txt

# Запускаємо твого агента
CMD ["streamlit", "run", "app.py", "--server.port", "8080"]
