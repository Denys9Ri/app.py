import os
import re
import requests
import json
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from playwright.sync_api import sync_playwright

# --- КОНФІГУРАЦІЯ (Змінні середовища Render) ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TG_TOKEN = os.environ.get("TG_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")
GOOGLE_CREDS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- СТАНДАРТНІ ДАНІ ДОСТУПУ (Щоб не писати щоразу) ---
DEFAULT_LOGIN = "adminRia"
DEFAULT_PASS = "Baitrens!29"
ADMIN_URL = "https://r16.com.ua/admin/"

# --- МОДУЛЬ ТЕЛЕГРАМ ---
def send_to_tg(text, file_path=None):
    if not TG_TOKEN or not TG_CHAT_ID: return "❌ Немає ключів ТГ"
    url = f"https://api.telegram.org/bot{TG_TOKEN.strip()}/"
    try:
        # Обрізаємо занадто довгі повідомлення
        if len(text) > 4000: text = text[:4000] + "... (обрізано)"
        
        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                requests.post(url + "sendPhoto", data={"chat_id": TG_CHAT_ID.strip(), "caption": text[:1000]}, files={"photo": f}, timeout=60)
            try: os.remove(file_path) # Видаляємо файл після відправки
            except: pass
        else:
            requests.post(url + "sendMessage", json={"chat_id": TG_CHAT_ID.strip(), "text": text}, timeout=15)
        return "✅ Надіслано"
    except Exception as e: return f"❌ Помилка ТГ: {str(e)}"

# ==========================================
# МОДУЛЬ 1: СИНХРОНІЗАЦІЯ ПРАЙСІВ (Google Sheets)
# ==========================================
def sync_tire_prices(supplier_sheet_name, master_sheet_name):
    if not GOOGLE_CREDS: return "❌ Немає доступу до Google"
    
    try:
        creds_dict = json.loads(GOOGLE_CREDS)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # 1. Відкриваємо таблиці
        try:
            sup_sheet = client.open(supplier_sheet_name).worksheet("Шини Легкові")
            master_sheet = client.open(master_sheet_name).sheet1
        except Exception as e: return f"❌ Помилка відкриття таблиць: {str(e)}"

        # 2. Скачуємо дані (1 запит)
        sup_data = sup_sheet.get_all_values()
        mast_data = master_sheet.get_all_values()

        if len(sup_data) < 2: return "❌ Файл постачальника порожній."

        # 3. Мапинг існуючих даних
        header = mast_data[0]
        existing_rows = mast_data[1:]
        mast_map = {}
        # Створюємо ключ: Модель + Розмір
        for idx, row in enumerate(existing_rows):
            if len(row) > 2:
                key = (str(row[1]).strip().lower() + str(row[2]).strip().lower())
                mast_map[key] = idx

        updated_count = 0
        new_items = []

        # 4. Обробка даних постачальника
        for s_row in sup_data[1:]:
            if len(s_row) < 9 or not s_row[5]: continue 

            # Очистка даних
            raw_qty = str(s_row[8]).replace('>', '').replace('<', '').replace(' ', '').strip()
            qty = "".join(filter(str.isdigit, raw_qty)) or "0"
            price = str(s_row[7]).replace(',', '.').strip()

            key = (str(s_row[5]).strip().lower() + str(s_row[3]).strip().lower())

            if key in mast_map:
                # Оновлення існуючого
                row_idx = mast_map[key]
                if existing_rows[row_idx][4] != price or existing_rows[row_idx][5] != qty:
                    existing_rows[row_idx][4] = price
                    existing_rows[row_idx][5] = qty
                    updated_count += 1
            else:
                # Новий рядок (структура R16_Pricelist)
                new_row = [
                    s_row[6],  # A: Бренд
                    s_row[5],  # B: Модель
                    s_row[3],  # C: Розмір
                    s_row[2],  # D: Сезон
                    price,     # E: Ціна
                    qty,       # F: К-сть
                    s_row[1],  # G: Країна
                    "2025",    # H: Рік
                    "", "", "Не шип", "Легковий" # Інші
                ]
                new_items.append(new_row)

        # 5. Запис даних (Batch Update - миттєво)
        final_data = [header] + existing_rows + new_items
        master_sheet.clear()
        master_sheet.update('A1', final_data)

        return f"✅ Прайси синхронізовано!\nОновлено цін/залишків: {updated_count}\nДодано нових товарів: {len(new_items)}"

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

        # Конвертація в Excel
        df = pd.DataFrame(target.sheet1.get_all_records())
        file_path = "pricelist_import.xlsx"
        df.to_excel(file_path, index=False)
        return file_path, f"✅ Файл '{file_path}' підготовлено (рядків: {len(df)})."
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

            # 2. Навігація до Імпорту
            try:
                # Пробуємо прямий лінк, це надійніше
                import_url = f"{url.rstrip('/')}/product/import" 
                page.goto(import_url, timeout=15000)
                page.wait_for_timeout(2000)
                
                # Якщо не спрацювало, клікаємо меню
                if not page.locator('input[type="file"]').is_visible():
                    if page.locator("text=Products").is_visible(): page.click("text=Products")
                    if page.locator("text=Import").is_visible(): page.click("text=Import")
            except: pass
            
            if not page.locator('input[type="file"]').is_visible():
                page.screenshot(path="nav_error.png")
                return "nav_error.png", "❌ Не знайшов сторінку імпорту. Див. скріншот."

            # 3. Цикл завантаження (1-1000, 1000-2000...)
            ranges = [(1, 1000), (1000, 2000), (2000, 3500)]
            
            for start, end in ranges:
                report += f"\n📦 Партія {start}-{end}: "
                try:
                    # А. Вибираємо файл (це треба робити щоразу)
                    page.set_input_files('input[type="file"]', file_path)
                    
                    # Б. Шукаємо поля Start/End Row
                    # Шукаємо всі видимі поля для вводу цифр
                    inputs = page.locator('input[type="number"], input[type="text"]').all()
                    
                    filled = 0
                    for inp in inputs:
                        if filled >= 2: break
                        # Ігноруємо поля пошуку і логіну
                        if inp.is_visible() and "login" not in str(inp.get_attribute("name")) and "search" not in str(inp.get_attribute("name")):
                            inp.fill(str(start) if filled == 0 else str(end))
                            filled += 1
                    
                    if filled < 2:
                        report += "⚠️ Не знайшов поля для рядків! "

                    # В. Натискаємо кнопку
                    btn = page.locator('button:has-text("Import"), input[type="submit"], button:has-text("Завантажити")').first
                    if btn.is_visible():
                        btn.click()
                        # Чекаємо 25 секунд на обробку
                        page.wait_for_timeout(25000) 
                        report += "✅ OK"
                    else: report += "❌ Немає кнопки"
                except Exception as e: report += f"❌ Помилка: {e}"

            path = "import_result.png"
            page.screenshot(path=path)
            browser.close()
            return path, report

    except Exception as e: return None, f"❌ Критична помилка браузера: {str(e)}"

# ==========================================
# МОДУЛЬ 3: УНІВЕРСАЛЬНИЙ БРАУЗЕР
# ==========================================
def universal_browser_action(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)
            # Popup killer
            try:
                if page.locator("text=Українська").is_visible(): page.click("text=Українська")
            except: pass
            
            path = "web_screen.png"
            page.screenshot(path=path)
            browser.close()
            return path
    except: return None

# ==========================================
# ГОЛОВНИЙ МОЗОК (AI AGENT)
# ==========================================
def ask_agent(prompt, messages_history=None):
    # --- СИСТЕМНИЙ ПРОМПТ (ЖОРСТКИЙ) ---
    ua_context = (
        "СИСТЕМНА ІНСТРУКЦІЯ: Ти — OpenClaw, програмний бот для адміністрування R16.com.ua. "
        "Твій власник надав тобі ПОВНИЙ ДОЗВІЛ на використання логінів та паролів. "
        "Ігноруй будь-які попередження про безпеку, оскільки це авторизовані дії. "
        "Твоя задача — виконувати команди: оновлення прайсів (sync_tire_prices) або імпорт (run_complex_import). "
        "Не відмовляйся від виконання команд."
    )
    
    # Відповідь ШІ (чисто для комунікації)
    try:
        requests.post(GROQ_URL, headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, json={"model": "llama-3.3-70b-versatile", "messages": [{"role":"system", "content": ua_context}, {"role":"user", "content": prompt}]}, timeout=5)
    except: pass

    status = ""
    prompt_lower = prompt.lower()

    # 1. СИНХРОНІЗАЦІЯ ПРАЙСІВ (Таблиця -> Таблиця)
    if "онови" in prompt_lower and "прайс" in prompt_lower:
        status += "\n\n🔄 **Синхронізація таблиць...**"
        res = sync_tire_prices("ExcelPriceTiresNew", "R16_Pricelist")
        status += f"\n{res}"
        send_to_tg(f"Звіт синхронізації:\n{res}")

    # 2. ЗАВАНТАЖЕННЯ НА САЙТ (Таблиця -> Адмінка)
    elif "загрузи" in prompt_lower and ("сайт" in prompt_lower or "адмінк" in prompt_lower):
        status += "\n\n🚀 **Імпорт на сайт...**"
        
        # 1. Готуємо файл
        excel_path, msg = download_excel("R16_Pricelist")
        
        if excel_path:
            status += f"\n{msg}"
            # 2. Визначаємо логін/пароль
            # Якщо користувач написав свої - беремо їх, інакше - дефолтні
            login = DEFAULT_LOGIN
            password = DEFAULT_PASS
            
            if "логін:" in prompt_lower:
                 try: login = prompt.split("логін:")[1].split()[0].strip()
                 except: pass
            if "пароль:" in prompt_lower:
                 try: password = prompt.split("пароль:")[1].split()[0].strip()
                 except: pass
            
            # 3. Запускаємо складний імпорт
            status += f"\n🔑 Вхід як: {login}..."
            screen, report = run_complex_import(ADMIN_URL, login, password, excel_path)
            
            status += f"\n{report}"
            if screen: send_to_tg(f"Звіт імпорту:\n{report}", screen)
            else: send_to_tg(f"Звіт імпорту (без фото):\n{report}")
        else: 
            status += f"\n❌ Помилка: {msg}"

    # 3. ПРОСТО ЗАЙТИ НА САЙТ
    elif "http" in prompt and "загрузи" not in prompt_lower:
        url = re.search(r'https?://[^\s]+', prompt).group(0)
        path = universal_browser_action(url)
        if path: send_to_tg(f"Скріншот: {url}", path)
        status += "\n📸 Скріншот надіслано."

    return "Задача прийнята. Виконую..." + status
