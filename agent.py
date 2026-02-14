import os
import re
import requests
import json
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from playwright.sync_api import sync_playwright

# --- КОНФІГУРАЦІЯ ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
TG_TOKEN = os.environ.get("TG_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")
GOOGLE_CREDS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- ТЕЛЕГРАМ ---
def send_to_tg(text, file_path=None):
    if not TG_TOKEN or not TG_CHAT_ID: return "❌ Немає ключів ТГ"
    url = f"https://api.telegram.org/bot{TG_TOKEN.strip()}/"
    try:
        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                requests.post(url + "sendPhoto", data={"chat_id": TG_CHAT_ID.strip(), "caption": text[:1000]}, files={"photo": f}, timeout=60)
            # os.remove(file_path) # Можна розкоментувати для очистки
        else:
            requests.post(url + "sendMessage", json={"chat_id": TG_CHAT_ID.strip(), "text": text[:4000]}, timeout=15)
        return "✅ Надіслано"
    except Exception as e: return f"❌ Помилка ТГ: {str(e)}"

# --- ЕКСПОРТ ТАБЛИЦІ В ФАЙЛ ---
def download_sheet_as_csv(sheet_name):
    if not GOOGLE_CREDS: return None, "❌ Немає доступу до Google"
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_CREDS), ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        client = gspread.authorize(creds)
        all_sheets = client.openall()
        target = next((s for s in all_sheets if sheet_name.lower() in s.title.lower()), None)
        if not target: return None, f"❌ Таблицю '{sheet_name}' не знайдено."

        df = pd.DataFrame(target.sheet1.get_all_records())
        file_path = "import_data.csv" # Стандартна назва для імпорту
        df.to_csv(file_path, index=False)
        return file_path, f"✅ Таблицю '{target.title}' скачано в CSV."
    except Exception as e: return None, f"❌ Помилка скачування: {str(e)}"

# --- УНІВЕРСАЛЬНИЙ БРАУЗЕР (Вхід + Дії) ---
def universal_browser_action(url, login=None, password=None, file_to_upload=None):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # Емуляція великого екрану
            context = browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
            page = context.new_page()
            
            print(f"🌍 Заходжу на: {url}")
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            report = f"Зайшов на {url}. "

            # 1. ЛОГІН (Якщо передано)
            if login and password:
                print("🔑 Пробую залогінитись...")
                try:
                    # Шукаємо типові поля логіна
                    user_selectors = ['input[name*="user"]', 'input[name*="login"]', 'input[name*="email"]', 'input[type="email"]']
                    pass_selectors = ['input[name*="pass"]', 'input[type="password"]']
                    
                    # Заповнюємо Логін
                    for sel in user_selectors:
                        if page.locator(sel).first.is_visible():
                            page.fill(sel, login)
                            break
                    
                    # Заповнюємо Пароль
                    for sel in pass_selectors:
                        if page.locator(sel).first.is_visible():
                            page.fill(sel, password)
                            page.press(sel, "Enter") # Тиснемо Enter
                            break
                    
                    page.wait_for_timeout(5000) # Чекаємо входу
                    report += "Спроба входу виконана. "
                except Exception as e:
                    report += f"⚠️ Помилка логіна: {str(e)}. "

            # 2. ЗАВАНТАЖЕННЯ ФАЙЛУ (Якщо є файл)
            if file_to_upload:
                print("📂 Шукаю куди завантажити файл...")
                try:
                    # Шукаємо будь-яке поле для файлу
                    file_input = page.locator('input[type="file"]').first
                    if file_input.is_visible():
                        file_input.set_input_files(file_to_upload)
                        report += "Файл вибрано. "
                        
                        # Шукаємо кнопку підтвердження (Імпорт/Save/Upload)
                        upload_btns = ['button:has-text("Import")', 'button:has-text("Upload")', 'input[type="submit"]', 'button:has-text("Зберегти")']
                        for btn in upload_btns:
                            if page.locator(btn).first.is_visible():
                                page.locator(btn).first.click()
                                report += "Кнопку імпорту натиснуто. "
                                break
                    else:
                        report += "⚠️ Поле для файлу (input type=file) не знайдено. "
                except Exception as e:
                    report += f"⚠️ Помилка завантаження: {str(e)}. "

            # 3. ФІНАЛЬНИЙ СКРІНШОТ
            path = "action_result.png"
            page.screenshot(path=path)
            browser.close()
            return path, report

    except Exception as e:
        return None, f"❌ Критична помилка браузера: {str(e)}"

# --- ПАРСЕР КОМАНД ---
def parse_credentials(text):
    # Шукаємо логін/пароль у тексті
    login = None
    password = None
    
    # Регулярки для пошуку "логін: ..."
    login_match = re.search(r'(?:логін|login)[:\s]+([^\s,]+)', text, re.IGNORECASE)
    pass_match = re.search(r'(?:пароль|pass|password)[:\s]+([^\s,]+)', text, re.IGNORECASE)
    
    if login_match: login = login_match.group(1)
    if pass_match: password = pass_match.group(1)
    
    return login, password

# --- ГОЛОВНИЙ АГЕНТ ---
def ask_agent(prompt, messages_history=None):
    # ШІ для балачок
    ua_context = "Ти — OpenClaw, універсальний бізнес-агент. Твоя задача — виконувати дії в браузері та таблицях."
    full_messages = [{"role": "system", "content": ua_context}]
    if messages_history: full_messages.extend(messages_history)
    full_messages.append({"role": "user", "content": prompt})
    
    try:
        res = requests.post(GROQ_URL, headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, json={"model": "llama-3.3-70b-versatile", "messages": full_messages}, timeout=20)
        bot_text = res.json()['choices'][0]['message']['content']
    except: bot_text = "Виконую..."

    status_report = ""

    # ЛОГІКА ДІЙ
    # 1. Витягуємо URL
    url_match = re.search(r'https?://[^\s]+', prompt)
    direct_url = url_match.group(0) if url_match else None
    
    # 2. Витягуємо Логін/Пароль
    user_login, user_pass = parse_credentials(prompt)
    
    # 3. Витягуємо Файл (якщо просять таблицю)
    file_path = None
    if "таблиц" in prompt.lower() and ("завантаж" in prompt.lower() or "імпорт" in prompt.lower()):
        # Спроба знайти назву таблиці або беремо дефолтну
        sheet_name = "clean_models_for_photos_merged" if "clean" in prompt.lower() else "R16_Pricelist"
        file_path, sheet_msg = download_sheet_as_csv(sheet_name)
        status_report += f"\n\n📊 {sheet_msg}"

    # 4. ЗАПУСК БРАУЗЕРА
    if direct_url:
        status_report += f"\n\n🌍 Запускаю браузер для {direct_url}..."
        if user_login: status_report += f"\n🔑 Логін: {user_login} | Пароль: *****"
        
        screenshot, browser_msg = universal_browser_action(direct_url, user_login, user_pass, file_to_upload=file_path)
        
        status_report += f"\n⚙️ {browser_msg}"
        if screenshot:
            send_to_tg(f"Звіт OpenClaw:\n{browser_msg}", screenshot)
            status_report += "\n✅ Скріншот надіслано в Telegram."

    elif "знайди" in prompt.lower():
        # Тут можна лишити пошук Tavily
        pass

    return bot_text + status_report
