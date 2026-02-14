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
TG_TOKEN = os.environ.get("TG_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")
GOOGLE_CREDS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- ТЕЛЕГРАМ ---
def send_to_tg(text, file_path=None):
    if not TG_TOKEN or not TG_CHAT_ID: return "❌ Немає ключів ТГ"
    url = f"https://api.telegram.org/bot{TG_TOKEN.strip()}/"
    try:
        # Обрізаємо довгий текст
        if len(text) > 4000: text = text[:4000] + "... (обрізано)"
        
        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                requests.post(url + "sendPhoto", data={"chat_id": TG_CHAT_ID.strip(), "caption": text[:1000]}, files={"photo": f}, timeout=60)
            try: os.remove(file_path) # Чистимо за собою
            except: pass
        else:
            requests.post(url + "sendMessage", json={"chat_id": TG_CHAT_ID.strip(), "text": text}, timeout=15)
        return "✅ Надіслано"
    except Exception as e: return f"❌ Помилка ТГ: {str(e)}"

# ==========================================
# МОДУЛЬ 1: СИНХРОНІЗАЦІЯ ПРАЙСІВ (Sheet -> Sheet)
# ==========================================
def sync_tire_prices(supplier_sheet_name, master_sheet_name):
    if not GOOGLE_CREDS: return "❌ Немає доступу до Google"
    
    try:
        creds_dict = json.loads(GOOGLE_CREDS)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Відкриваємо таблиці
        try:
            sup_sheet = client.open(supplier_sheet_name).worksheet("Шини Легкові")
            master_sheet = client.open(master_sheet_name).sheet1
        except Exception as e: return f"❌ Помилка відкриття таблиць: {str(e)}"

        # Скачуємо дані
        sup_data = sup_sheet.get_all_values()
        mast_data = master_sheet.get_all_values()

        if len(sup_data) < 2: return "❌ Файл постачальника порожній."

        # Мапинг існуючих даних
        header = mast_data[0]
        existing_rows = mast_data[1:]
        mast_map = {}
        for idx, row in enumerate(existing_rows):
            if len(row) > 2:
                key = (str(row[1]).strip().lower() + str(row[2]).strip().lower())
                mast_map[key] = idx

        updated_count = 0
        new_items = []

        # Обробка даних постачальника
        for s_row in sup_data[1:]:
            if len(s_row) < 9 or not s_row[5]: continue 

            # Очистка
            raw_qty = str(s_row[8]).replace('>', '').replace('<', '').replace(' ', '').strip()
            qty = "".join(filter(str.isdigit, raw_qty)) or "0"
            price = str(s_row[7]).replace(',', '.').strip()

            key = (str(s_row[5]).strip().lower() + str(s_row[3]).strip().lower())

            if key in mast_map:
                # Оновлення
                row_idx = mast_map[key]
                if existing_rows[row_idx][4] != price or existing_rows[row_idx][5] != qty:
                    existing_rows[row_idx][4] = price
                    existing_rows[row_idx][5] = qty
                    updated_count += 1
            else:
                # Новий рядок
                new_row = [s_row[6], s_row[5], s_row[3], s_row[2], price, qty, s_row[1], "2025", "", "", "Не шип", "Легковий"]
                new_items.append(new_row)

        # Batch Update (Швидкий запис)
        final_data = [header] + existing_rows + new_items
        master_sheet.clear()
        master_sheet.update('A1', final_data)

        return f"✅ Прайси синхронізовано!\nОновлено: {updated_count}\nДодано нових: {len(new_items)}"

    except Exception as e: return f"❌ Помилка синхронізації: {str(e)}"

# ==========================================
# МОДУЛЬ 2: ІМПОРТ В АДМІНКУ (Excel -> Site)
# ==========================================
def download_excel(sheet_name):
    if not GOOGLE_CREDS: return None, "❌ Немає доступу до Google"
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_CREDS), ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        client = gspread.authorize(creds)
        target = next((s for s in client.openall() if sheet_name.lower() in s.title.lower()), None)
        
        if not target: return None, f"❌ Таблицю '{sheet_name}' не знайдено."

        df = pd.DataFrame(target.sheet1.get_all_records())
        file_path = "pricelist_import.xlsx"
        df.to_excel(file_path, index=False)
        return file_path, f"✅ Файл '{file_path}' підготовлено."
    except Exception as e: return None, f"❌ Помилка Excel: {str(e)}"

def run_complex_import(url, login, password, file_path):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="uk-UA")
            page = context.new_page()
            report = ""

            # 1. Логін
            print(f"🔑 Вхід в адмінку: {url}")
            page.goto(url, timeout=60000)
            try:
                page.fill('input[name*="login"], input[name*="user"]', login)
                page.fill('input[type="password"]', password)
                page.press('input[type="password"]', "Enter")
                page.wait_for_timeout(5000)
            except Exception as e: return None, f"❌ Не вдалося залогінитись: {e}"

            # 2. Навігація (Products -> Import)
            try:
                page.goto(f"{url.rstrip('/')}/product/import", timeout=15000)
                page.wait_for_timeout(2000)
                if not page.locator('input[type="file"]').is_visible():
                    # Якщо пряме посилання не спрацювало, шукаємо в меню
                    if page.locator("text=Products").is_visible(): page.click("text=Products")
                    if page.locator("text=Import").is_visible(): page.click("text=Import")
            except: pass
            
            if not page.locator('input[type="file"]').is_visible():
                page.screenshot(path="nav_error.png")
                return "nav_error.png", "❌ Не знайшов сторінку імпорту."

            # 3. Цикл завантаження (1-1000, 1000-2000...)
            ranges = [(1, 1000), (1000, 2000), (2000, 3500)]
            
            for start, end in ranges:
                report += f"\n📦 Партія {start}-{end}: "
                try:
                    page.set_input_files('input[type="file"]', file_path)
                    
                    # Шукаємо поля введення (Start/End)
                    inputs = page.locator('input[type="number"], input[type="text"]').all()
                    filled = 0
                    for inp in inputs:
                        if filled >= 2: break
                        if inp.is_visible() and "login" not in str(inp.get_attribute("name")):
                            inp.fill(str(start) if filled == 0 else str(end))
                            filled += 1
                    
                    # Тиснемо кнопку
                    btn = page.locator('button:has-text("Import"), input[type="submit"], button:has-text("Завантажити")').first
                    if btn.is_visible():
                        btn.click()
                        page.wait_for_timeout(20000) # Чекаємо обробку
                        report += "✅ OK"
                    else: report += "❌ Немає кнопки"
                except Exception as e: report += f"❌ Помилка: {e}"

            path = "import_result.png"
            page.screenshot(path=path)
            browser.close()
            return path, report

    except Exception as e: return None, f"❌ Критична помилка: {str(e)}"

# ==========================================
# МОДУЛЬ 3: УНІВЕРСАЛЬНИЙ БРАУЗЕР (Для всього іншого)
# ==========================================
def universal_browser_action(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)
            path = "web_screen.png"
            page.screenshot(path=path)
            browser.close()
            return path
    except: return None

# ==========================================
# ГОЛОВНИЙ МОЗОК
# ==========================================
def ask_agent(prompt, messages_history=None):
    ua_context = "Ти — техпрацівник R16. В тебе є 3 функції: sync_tire_prices, run_complex_import, universal_browser_action."
    
    # Відповідь ШІ
    try:
        requests.post(GROQ_URL, headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, json={"model": "llama-3.3-70b-versatile", "messages": [{"role":"system", "content": ua_context}, {"role":"user", "content": prompt}]}, timeout=5)
    except: pass

    status = ""

    # 1. СИНХРОНІЗАЦІЯ ПРАЙСІВ (Таблиця -> Таблиця)
    if "онови" in prompt.lower() and "прайс" in prompt.lower():
        status += "\n\n🔄 **Синхронізація таблиць...**"
        res = sync_tire_prices("ExcelPriceTiresNew", "R16_Pricelist")
        status += f"\n{res}"
        send_to_tg(f"Звіт синхронізації:\n{res}")

    # 2. ЗАВАНТАЖЕННЯ НА САЙТ (Таблиця -> Адмінка)
    elif "загрузи" in prompt.lower() and "сайт" in prompt.lower():
        status += "\n\n🚀 **Імпорт на сайт...**"
        excel_path, msg = download_excel("R16_Pricelist")
        if excel_path:
            # Дані для входу
            login = "adminRia"
            password = "Baitrens!29"
            if "логін:" in prompt.lower():
                 try: login = prompt.split("логін:")[1].split()[0].strip()
                 except: pass
            
            screen, report = run_complex_import("https://r16.com.ua/admin/", login, password, excel_path)
            status += f"\n{report}"
            if screen: send_to_tg(f"Звіт імпорту:\n{report}", screen)
        else: status += f"\n{msg}"

    # 3. ПРОСТО ЗАЙТИ НА САЙТ
    elif "http" in prompt and "загрузи" not in prompt:
        url = re.search(r'https?://[^\s]+', prompt).group(0)
        path = universal_browser_action(url)
        if path: send_to_tg(f"Скріншот: {url}", path)
        status += "\n📸 Скріншот надіслано."

    return "Задача виконується. Звіт у Telegram." + status
