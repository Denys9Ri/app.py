import os
import requests
from playwright.sync_api import sync_playwright
from telethon import TelegramClient

# Налаштування
GROQ_API_KEY = "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"
TG_TOKEN = os.environ.get("TG_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")

# --- ІНСТРУМЕНТ 1: Скріншот сайту ---
def take_screenshot(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        path = "screenshot.png"
        page.screenshot(path=path)
        browser.close()
        return path

# --- ІНСТРУМЕНТ 2: Відправка в ТГ (з файлом) ---
def send_to_telegram(text, file_path=None):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/"
    if file_path:
        with open(file_path, "rb") as f:
            requests.post(url + "sendPhoto", data={"chat_id": TG_CHAT_ID, "caption": text}, files={"photo": f})
    else:
        requests.post(url + "sendMessage", json={"chat_id": TG_CHAT_ID, "text": text})
    return "✅ Відправлено в Telegram"

# --- ОСНОВНИЙ МОЗОК ---
def ask_agent(prompt, messages_history=None):
    # Тут логіка Groq, яку ми вже налаштували, 
    # але з додаванням обробки команд (скріншот, аналіз, ТГ)
    # ... (код аналогічний попередньому, але з викликом функцій вище)
