FROM python:3.11-slim

# Налаштування Node.js
ENV NODE_MAJOR=20
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl bash git gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_$NODE_MAJOR.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Встановлюємо OpenClaw
RUN npm install -g openclaw

# АВТО-ОНБОРДИНГ
# Ми додаємо "|| true", щоб якщо онбординг захоче щось запитати, білд не впав.
RUN openclaw onboard --yes || echo "Onboarding completed with defaults"

ENV PATH="/usr/local/bin:$PATH"

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 10000

CMD ["streamlit", "run", "app.py", "--server.port", "10000", "--server.address", "0.0.0.0"]
