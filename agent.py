import os
import requests
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from playwright.sync_api import sync_playwright

# Налаштування ключів
GROQ_API_KEY = "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"
URL = "https://api.groq.com/openai/v1/chat/completions"

# Конфігурація Google (беремо з Env Variables на Render)
GOOGLE_CREDS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")

# --- ІНСТРУМЕНТ: Скріншот ---
def take_screenshot(target_url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(target_url, timeout=60000)
            path = "screenshot.png"
            page.screenshot(path=path)
            browser.close()
            return path
    except Exception as e:
        return f"Error: {str(e)}"

# --- ІНСТРУМЕНТ: Google Таблиці ---
def update_sheet(sheet_name, row_data):
    try:
        creds_dict = json.loads(GOOGLE_CREDS)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(sheet_name).sheet1
        sheet.append_row(row_data)
        return "✅ Дані додано в таблицю"
    except Exception as e:
        return f"❌ Помилка Google Sheets: {str(e)}"

# --- ІНСТРУМЕНТ: Telegram ---
def send_to_tg(text, file_path=None):
    token = os.environ.get("TG_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    if not token or not chat_id: return "Помилка конфігурації ТГ"
    
    url = f"https://api.telegram.org/bot{token}/"
    if file_path:
        with open(file_path, "rb") as f:
            requests.post(url + "sendPhoto", data={"chat_id": chat_id, "caption": text}, files={"photo": f})
    else:
        requests.post(url + "sendMessage", json={"chat_id": chat_id, "text": text})
    return "ОК"

def ask_agent(prompt, messages_history=None):
    ua_context = (
        "Ти — OpenClaw, автономний агент R16.com.ua. Ти вмієш: "
        "1. Робити скріншоти сайтів. 2. Працювати з Google Таблицями. 3. Надсилати звіти в Telegram. "
        "Відповідай завжди українською."
    )
    
    # Логіка Groq з пам'яттю
    full_messages = [{"role": "system", "content": ua_context}]
    if messages_history:
        for msg in messages_history:
            full_messages.append({"role": msg["role"], "content": msg["content"]})
    full_messages.append({"role": "user", "content": prompt})
    
    # Виклик моделі
    res = requests.post(URL, headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, 
                        json={"model": "llama-3.3-70b-versatile", "messages": full_messages})
    bot_text = res.json()['choices'][0]['message']['content']

    # ПЕРЕВІРКА КОМАНД
    if "скріншот" in prompt.lower():
        path = take_screenshot("https://r16.com.ua")
        send_to_tg("Ось твій скріншот, Денисе!", path)
        bot_text += "\n\n[Системне: Скріншот надіслано в ТГ]"
        
    if "запиши в таблицю" in prompt.lower():
        # Приклад запису (можна налаштувати динамічно)
        status = update_sheet("R16_Pricelist", ["Тест", "Шина R16", "2500 грн"])
        bot_text += f"\n\n[Системне: {status}]"

    return bot_text
def send_to_tg(text, file_path=None):
    token = os.environ.get("TG_TOKEN", "").strip()
    chat_id = os.environ.get("TG_CHAT_ID", "").strip()
    
    if not token or not chat_id:
        return "❌ Помилка: Токен або Chat ID не встановлені в Render!"
        
    url = f"https://api.telegram.org/bot{token}/"
    try:
        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                res = requests.post(url + "sendPhoto", data={"chat_id": chat_id, "caption": text}, files={"photo": f})
        else:
            res = requests.post(url + "sendMessage", json={"chat_id": chat_id, "text": text})
        
        if res.status_code == 200:
            return "✅ Успішно надіслано в Telegram"
        else:
            return f"❌ Помилка Telegram: {res.text}" # Це покаже нам справжню причину
    except Exception as e:
        return f"❌ Помилка зв'язку: {str(e)}"
