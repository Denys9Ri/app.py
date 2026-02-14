import os
import re
import requests
import json
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# --- КОНФІГУРАЦІЯ ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TG_TOKEN = os.environ.get("TG_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")
GOOGLE_CREDS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- СТАНДАРТНІ ДАНІ ---
DEFAULT_LOGIN = "adminRia"
DEFAULT_PASS = "Baitrens!29"
ADMIN_URL = "https://r16.com.ua/admin/"
IMPORT_URL = "https://r16.com.ua/admin/store/product/import-excel/"

# --- ТЕЛЕГРАМ ---
def send_to_tg(text, file_path=None):
    if not TG_TOKEN or not TG_CHAT_ID: return "❌ Немає ключів ТГ"
    url = f"https://api.telegram.org/bot{TG_TOKEN.strip()}/"
    try:
        if len(text) > 4000: text = text[:4000] + "..."
        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                requests.post(url + "sendPhoto", data={"chat_id": TG_CHAT_ID.strip(), "caption": text[:1000]}, files={"photo": f}, timeout=60)
            try: os.remove(file_path)
            except: pass
        else:
            requests.post(url + "sendMessage", json={"chat_id": TG_CHAT_ID.strip(), "text": text}, timeout=15)
        return "✅ Надіслано"
    except Exception as e: return f"❌ Помилка ТГ: {str(e)}"

def safe_screenshot(page, path):
    try:
        page.screenshot(path=path, timeout=5000, animations="disabled")
        return path
    except: return None

# ==========================================
# МОДУЛЬ 1: СИНХРОНІЗАЦІЯ ПРАЙСІВ
# ==========================================
def sync_tire_prices(supplier_sheet_name, master_sheet_name):
    if not GOOGLE_CREDS: return "❌ Немає доступу до Google"
    try:
        creds_dict = json.loads(GOOGLE_CREDS)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        sup_sheet = client.open(supplier_sheet_name).worksheet("Шини Легкові")
        master_sheet = client.open(master_sheet_name).sheet1

        sup_data = sup_sheet.get_all_values()
        mast_data = master_sheet.get_all_values()

        header = mast_data[0]
        existing_rows = mast_data[1:]
        mast_map = { (str(row[1]).strip().lower() + str(row[2]).strip().lower()): idx for idx, row in enumerate(existing_rows) if len(row) > 2 }

        updated_count = 0
        new_items = []

        for s_row in sup_data[1:]:
            if len(s_row) < 9 or not s_row[5]: continue 
            qty = "".join(filter(str.isdigit, str(s_row[8]).replace(' ', ''))) or "0"
            price = str(s_row[7]).replace(',', '.').strip()
            key = (str(s_row[5]).strip().lower() + str(s_row[3]).strip().lower())

            if key in mast_map:
                row_idx = mast_map[key]
                if existing_rows[row_idx][4] != price or existing_rows[row_idx][5] != qty:
                    existing_rows[row_idx][4] = price
                    existing_rows[row_idx][5] = qty
                    updated_count += 1
            else:
                new_row = [s_row[6], s_row[5], s_row[3], s_row[2], price, qty, s_row[1], "2025", "", "", "Не шип", "Легковий"]
                new_items.append(new_row)

        final_data = [header] + existing_rows + new_items
        master_sheet.clear()
        master_sheet.update('A1', final_data)
        return f"✅ Синхронізовано: оновлено {updated_count}, додано {len(new_items)}"
    except Exception as e: return f"❌ Помилка: {str(e)}"

# ==========================================
# МОДУЛЬ 2: ІМПОРТ (ПО 500 РЯДКІВ)
# ==========================================
def download_excel(sheet_name):
    if not GOOGLE_CREDS: return None, "❌ Помилка Google"
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_CREDS), ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        client = gspread.authorize(creds)
        target = next((s for s in client.openall() if sheet_name.lower() in s.title.lower()), None)
        df = pd.DataFrame(target.sheet1.get_all_records())
        file_path = "pricelist_import.xlsx"
        df.to_excel(file_path, index=False)
        return file_path, f"✅ Файл готовий ({len(df)} рядків)."
    except Exception as e: return None, f"❌ Помилка Excel: {str(e)}"

def run_complex_import(base_url, login, password, file_path):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--disable-web-security'])
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()
            report = ""

            # 1. Логін
            page.goto(base_url, timeout=60000)
            page.fill('input[name*="login"], input[name*="user"]', login)
            page.fill('input[type="password"]', password)
            page.press('input[type="password"]', "Enter")
            page.wait_for_timeout(5000)

            # 2. Сторінка імпорту
            page.goto(IMPORT_URL, timeout=45000)
            page.wait_for_timeout(3000)

            if not page.locator('input[type="file"]').is_visible():
                return safe_screenshot(page, "error.png"), "❌ Форма імпорту не знайдена."

            # 3. Цикл по 500 рядків
            # Робимо список пар: (1, 500), (501, 1000), ..., (3001, 3500)
            ranges = [(i, i + 499) for i in range(1, 3501, 500)]
            
            for start, end in ranges:
                report += f"\n📦 {start}-{end}: "
                try:
                    page.set_input_files('input[type="file"]', file_path)
                    
                    # Шукаємо поля для введення цифр
                    inputs = page.locator('input[type="number"], input[type="text"]').all()
                    filled = 0
                    for inp in inputs:
                        if filled >= 2: break
                        if inp.is_visible():
                             name = str(inp.get_attribute("name")).lower()
                             if "search" not in name and "login" not in name:
                                inp.fill(str(start) if filled == 0 else str(end))
                                filled += 1
                    
                    btn = page.locator('button:has-text("Import"), input[type="submit"], button:has-text("Завантажити")').first
                    if btn.is_visible():
                        btn.click()
                        # ЧЕКАЄМО ДОВШЕ (45 сек), бо сайт повільний
                        page.wait_for_timeout(45000) 
                        report += "✅"
                    else: report += "❌ кнопка?"
                except Exception as e: report += f"⚠️ помилка"

            path = safe_screenshot(page, "final_res.png")
            browser.close()
            return path, report
    except Exception as e: return None, f"❌ Помилка: {str(e)}"

# ==========================================
# ГОЛОВНИЙ МОЗОК
# ==========================================
def ask_agent(prompt, messages_history=None):
    ua_context = "Ти — адмін-бот R16. Виконуй команди."
    try: requests.post(GROQ_URL, headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, json={"model": "llama-3.3-70b-versatile", "messages": [{"role":"system", "content": ua_context}, {"role":"user", "content": prompt}]}, timeout=5)
    except: pass

    status = ""
    p_low = prompt.lower()

    if "онови" in p_low and "прайс" in p_low:
        status += "\n\n🔄 **Синхронізація таблиць...**"
        res = sync_tire_prices("ExcelPriceTiresNew", "R16_Pricelist")
        status += f"\n{res}"
        send_to_tg(f"Звіт синхронізації:\n{res}")

    elif "загрузи" in p_low and ("сайт" in p_low or "адмінк" in p_low):
        status += "\n\n🚀 **Імпорт (по 500 рядків)...**"
        file, msg = download_excel("R16_Pricelist")
        if file:
            status += f"\n{msg}"
            screen, report = run_complex_import(ADMIN_URL, DEFAULT_LOGIN, DEFAULT_PASS, file)
            status += f"\n{report}"
            send_to_tg(f"Звіт імпорту:\n{report}", screen)
        else: status += f"\n❌ {msg}"

    return "Виконую..." + status
