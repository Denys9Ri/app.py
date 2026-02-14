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
        else:
            requests.post(url + "sendMessage", json={"chat_id": TG_CHAT_ID.strip(), "text": text[:4000]}, timeout=15)
        return "✅ Надіслано"
    except Exception as e: return f"❌ Помилка ТГ: {str(e)}"

# --- ФУНКЦІЯ СИНХРОНІЗАЦІЇ ПРАЙСІВ (ОНОВЛЕНА ПІД ТВОЮ СТРУКТУРУ) ---
def sync_tire_prices(supplier_sheet_name, master_sheet_name):
    if not GOOGLE_CREDS: return "❌ Немає доступу до Google"
    
    try:
        creds_dict = json.loads(GOOGLE_CREDS)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # 1. Відкриваємо таблиці
        try:
            # Відкриваємо постачальника на конкретному листі "Шини Легкові"
            sup_book = client.open(supplier_sheet_name)
            sup_sheet = sup_book.worksheet("Шини Легкові") 
            
            master_book = client.open(master_sheet_name)
            master_sheet = master_book.sheet1
        except Exception as e:
            return f"❌ Не знайшов таблиці або лист: {str(e)}"

        # 2. Скачуємо дані
        sup_data = sup_sheet.get_all_values()
        mast_data = master_sheet.get_all_values()

        if len(sup_data) < 2: return "❌ Файл постачальника порожній."

        # Словник твого файлу для швидкого пошуку (Ключ: назва + розмір)
        mast_map = {}
        for idx, row in enumerate(mast_data[1:], start=2):
            if len(row) > 2:
                # Ключ: Модель(B) + Типорозмір(C) в нижньому регістрі
                key = (str(row[1]).strip().lower() + str(row[2]).strip().lower())
                mast_map[key] = idx

        updated_count = 0
        new_items = []

        # 3. Обробка рядків постачальника
        for s_row in sup_data[1:]:
            if len(s_row) < 9 or not s_row[5]: continue # Пропуск порожніх

            # Очистка залишку (20< -> 20)
            raw_qty = str(s_row[8]).replace('>', '').replace('<', '').strip()
            qty = "".join(filter(str.isdigit, raw_qty))
            if not qty: qty = "0"

            # Створюємо рядок за ТВОЄЮ структурою (Скрін 11)
            # A:Бренд(G), B:Модель(F), C:Типорозмір(D), D:Сезон(C), E:Ціна(H), F:Кол-во(I), G:Країна(B)
            new_row = [
                s_row[6],  # A: Бренд (Виробник у пост.)
                s_row[5],  # B: Модель (Товар у пост.)
                s_row[3],  # C: Типорозмір
                s_row[2],  # D: Сезон (Сезонність у пост.)
                s_row[7],  # E: Ціна (Ваша ціна у пост.)
                qty,       # F: Кол-во (Залишок у пост.)
                s_row[1],  # G: Країна
                "2025",    # H: Рік
                "", "", "Не шип", "Легковий" # Інші колонки дефолтні
            ]

            key = (str(new_row[1]).strip().lower() + str(new_row[2]).strip().lower())

            if key in mast_map:
                # ОНОВЛЮЄМО ІСНУЮЧИЙ (Ціна в E/5, Кількість в F/6)
                row_num = mast_map[key]
                master_sheet.update_cell(row_num, 5, new_row[4])
                master_sheet.update_cell(row_num, 6, new_row[5])
                updated_count += 1
            else:
                # ДОДАЄМО НОВИЙ
                new_items.append(new_row)

        if new_items:
            master_sheet.append_rows(new_items)

        return f"✅ Синхронізація завершена! Оновлено: {updated_count}. Додано нових: {len(new_items)}."

    except Exception as e:
        return f"❌ Помилка: {str(e)}"

# --- УНІВЕРСАЛЬНИЙ БРАУЗЕР (Вхід + Дії) ---
def universal_browser_action(url, login=None, password=None, search_query=None):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            page.goto(url, timeout=60000)
            
            # Popup killer (мова)
            for sel in ["text=Українська", "text=UA", "text=Зрозуміло"]:
                try: 
                    if page.locator(sel).is_visible(): page.locator(sel).first.click()
                except: pass

            if login and password:
                # Спроба логіна
                try:
                    page.fill('input[name*="login"], input[name*="user"]', login)
                    page.fill('input[type="password"]', password)
                    page.press('input[type="password"]', "Enter")
                    page.wait_for_timeout(5000)
                except: pass

            if search_query:
                try:
                    page.fill('input[type="search"], input[name="q"]', search_query)
                    page.press('input[type="search"], input[name="q"]', "Enter")
                    page.wait_for_timeout(3000)
                except: pass

            path = "web_result.png"
            page.screenshot(path=path)
            browser.close()
            return path
    except Exception as e: return None

# --- ГОЛОВНИЙ АГЕНТ ---
def ask_agent(prompt, messages_history=None):
    ua_context = (
        "Ти — OpenClaw, автономний асистент R16.com.ua. "
        "Якщо просять оновити прайси — запускай sync_tire_prices. "
        "Якщо є посилання — використовуй universal_browser_action."
    )
    
    messages = [{"role": "system", "content": ua_context}]
    if messages_history: messages.extend(messages_history)
    messages.append({"role": "user", "content": prompt})
    
    try:
        res = requests.post(GROQ_URL, headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, 
                            json={"model": "llama-3.3-70b-versatile", "messages": messages}, timeout=20)
        bot_text = res.json()['choices'][0]['message']['content']
    except: bot_text = "Працюю..."

    status = ""
    
    # 1. Логіка прайсів
    if "онови" in prompt.lower() and "прайс" in prompt.lower():
        status += "\n\n🔄 **Запускаю реальну синхронізацію...**"
        res_sync = sync_tire_prices("ExcelPriceTiresNew", "R16_Pricelist")
        status += f"\n{res_sync}"

    # 2. Логіка браузера
    url_match = re.search(r'https?://[^\s]+', prompt)
    if url_match:
        url = url_match.group(0)
        status += f"\n\n🌍 **Заходжу на сайт...**"
        path = universal_browser_action(url)
        tg_msg = send_to_tg(f"Скріншот для Дениса: {url}", path)
        status += f"\nTelegram: {tg_msg}"

    return bot_text + status
