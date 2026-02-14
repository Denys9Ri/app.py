import os
import requests
import json
from playwright.sync_api import sync_playwright

GROQ_API_KEY = "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"
URL = "https://api.groq.com/openai/v1/chat/completions"

# --- ФУНКЦІЯ 1: Скріншот (Руки) ---
def take_screenshot(target_url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(target_url, timeout=60000)
            screenshot_path = "screenshot.png"
            page.screenshot(path=screenshot_path)
            browser.close()
            return screenshot_path
    except Exception as e:
        return f"Помилка скріншоту: {str(e)}"

# --- ФУНКЦІЯ 2: Відправка в ТГ (якщо просять скріншот) ---
def send_to_tg(text, file_path=None):
    token = os.environ.get("TG_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    if not token or not chat_id: return "Помилка: Немає токенів ТГ"
    
    base_url = f"https://api.telegram.org/bot{token}/"
    if file_path and os.path.exists(file_path):
        with open(file_path, "rb") as f:
            requests.post(base_url + "sendPhoto", data={"chat_id": chat_id, "caption": text}, files={"photo": f})
    else:
        requests.post(base_url + "sendMessage", json={"chat_id": chat_id, "text": text})
    return "Надіслано!"

def ask_agent(prompt, messages_history=None):
    # Додаємо в промпт інструкцію про "руки"
    ua_context = (
        "Ти — OpenClaw, автономний агент R16.com.ua. Ти маєш доступ до інструментів: "
        "1. Скріншот сайту. 2. Відправка файлів у Telegram. 3. Аналіз прайсів. "
        "Якщо тебе просять зробити скріншот — кажи 'Зараз зроблю' і виконуй."
    )
    
    # ... (код запиту до Groq як раніше) ...
    
    # ЛОГІКА ДЛЯ СКРІНШОТА
    if "скріншот" in prompt.lower() or "зроби фото сайта" in prompt.lower():
        # Шукаємо URL у промпті або використовуємо твій сайт
        target = "https://r16.com.ua"
        path = take_screenshot(target)
        status = send_to_tg(f"Ось скріншот сайту {target}", path)
        return f"Я зайшов на сайт, зробив скріншот і відправив тобі в Telegram. Стан: {status}"

    # Звичайний запит до Groq
    # (Тут твоя логіка з messages_history)
