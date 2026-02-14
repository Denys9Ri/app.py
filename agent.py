import os
import re
import requests
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from playwright.sync_api import sync_playwright

# --- КОНФІГУРАЦІЯ (Беремо з Render) ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
TG_TOKEN = os.environ.get("TG_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")
GOOGLE_CREDS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- ІНСТРУМЕНТ: ТЕЛЕГРАМ ---
def send_to_tg(text, file_path=None):
    if not TG_TOKEN or not TG_CHAT_ID: return "❌ Немає ключів ТГ"
    url = f"https://api.telegram.org/bot{TG_TOKEN.strip()}/"
    try:
        # Telegram має ліміт на довжину тексту, тому ріжемо якщо задовгий
        if len(text) > 4000: text = text[:4000] + "... (обрізано)"

        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                requests.post(url + "sendPhoto", data={"chat_id": TG_CHAT_ID.strip(), "caption": text[:1000]}, files={"photo": f}, timeout=60)
            # Видаляємо файл після відправки, щоб не забивати пам'ять
            try: os.remove(file_path)
            except: pass
        else:
            requests.post(url + "sendMessage", json={"chat_id": TG_CHAT_ID.strip(), "text": text}, timeout=15)
        return "✅ Надіслано"
    except Exception as e: return f"❌ Помилка ТГ: {str(e)}"

# --- ІНСТРУМЕНТ: СИНХРОНІЗАЦІЯ ПРАЙСІВ (Batch Update) ---
def sync_tire_prices(supplier_sheet_name, master_sheet_name):
    if not GOOGLE_CREDS: return "❌ Немає доступу до Google"
    
    try:
        creds_dict = json.loads(GOOGLE_CREDS)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # 1. Відкриваємо таблиці
        try:
            sup_book = client.open(supplier_sheet_name)
            sup_sheet = sup_book.worksheet("Шини Легкові") # Важливо: точна назва листа
            
            master_book = client.open(master_sheet_name)
            master_sheet = master_book.sheet1
        except Exception as e:
            return f"❌ Не знайшов таблицю або лист. Помилка: {str(e)}"

        # 2. Скачуємо ВСІ дані (це 1 запит)
        print("📥 Скачую прайси...")
        sup_data = sup_sheet.get_all_values()
        mast_data = master_sheet.get_all_values()

        if len(sup_data) < 2: return "❌ Файл постачальника порожній."

        # 3. Підготовка Майстер-даних
        header = mast_data[0] # Зберігаємо шапку (Бренд, Модель, ...)
        existing_rows = mast_data[1:] # Дані без шапки
        
        # Створюємо мапу для швидкого пошуку: Ключ (Модель+Розмір) -> Індекс в списку
        mast_map = {}
        for idx, row in enumerate(existing_rows):
            if len(row) > 2:
                # Нормалізуємо ключ: маленькі літери, без пробілів
                key = (str(row[1]).strip().lower() + str(row[2]).strip().lower())
                mast_map[key] = idx

        updated_count = 0
        new_items = []

        # 4. Проходимо по Постачальнику (в пам'яті)
        for s_row in sup_data[1:]: # Пропускаємо шапку постачальника
            # Перевірка на цілісність рядка (мінімум колонок) та наявність назви товару
            if len(s_row) < 9 or not s_row[5]: continue 

            # ОЧИСТКА ЗАЛИШКУ: "20<" -> "20", "В дорозі" -> "0"
            raw_qty = str(s_row[8]).replace('>', '').replace('<', '').replace(' ', '').strip()
            qty = "".join(filter(str.isdigit, raw_qty))
            if not qty: qty = "0"

            # ОЧИСТКА ЦІНИ: замінюємо коми на крапки якщо треба
            price = str(s_row[7]).replace(',', '.').strip()

            # ФОРМУВАННЯ КЛЮЧА (Товар + Типорозмір)
            key = (str(s_row[5]).strip().lower() + str(s_row[3]).strip().lower())

            if key in mast_map:
                # --- ОНОВЛЕННЯ ІСНУЮЧОГО ---
                row_idx = mast_map[key]
                # Оновлюємо тільки Ціну (Індекс 4 / Col E) та Кількість (Індекс 5 / Col F)
                # Перевіряємо, чи змінились дані, щоб дарма не рахувати
                if existing_rows[row_idx][4] != price or existing_rows[row_idx][5] != qty:
                    existing_rows[row_idx][4] = price
                    existing_rows[row_idx][5] = qty
                    updated_count += 1
            else:
                # --- ДОДАВАННЯ НОВОГО ---
                # Формуємо рядок під твою структуру R16_Pricelist:
                # A:Бренд, B:Модель, C:Типорозмір, D:Сезон, E:Ціна, F:К-сть, G:Країна, H:Рік, ...
                new_row = [
                    s_row[6],  # A: Бренд (з G постачальника)
                    s_row[5],  # B: Модель (з F)
                    s_row[3],  # C: Розмір (з D)
                    s_row[2],  # D: Сезон (з C)
                    price,     # E: Ціна (з H)
                    qty,       # F: К-сть (з I)
                    s_row[1],  # G: Країна (з B)
                    "2025",    # H: Рік (Дефолт)
                    "", "", "Не шип", "Легковий" # I, J, K, L (Дефолт)
                ]
                new_items.append(new_row)

        # 5. ЗАПИС ДАНИХ (Batch Update - 1 запит)
        print("💾 Зберігаю дані...")
        final_data = [header] + existing_rows + new_items
        
        # Очищуємо лист і записуємо нові дані повністю
        master_sheet.clear()
        master_sheet.update('A1', final_data)

        return f"✅ Прайси оновлено!\nЗмінено цін/залишків: {updated_count}\nДодано нових товарів: {len(new_items)}"

    except Exception as e:
        return f"❌ Критична помилка синхронізації: {str(e)}"

# --- ІНСТРУМЕНТ: УНІВЕРСАЛЬНИЙ БРАУЗЕР (Вхід + Дії + Popup Killer) ---
def universal_browser_action(url, login=None, password=None, search_query=None):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1920, "height": 1080}, locale="uk-UA")
            page = context.new_page()
            
            print(f"🌍 Заходжу на: {url}")
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

            # --- POPUP KILLER (Закриваємо мовні вікна) ---
            popups = ["text=Українська", "text=UA", "text=Зрозуміло", "text=Прийняти", "button[aria-label='Close']"]
            for p_sel in popups:
                try: 
                    if page.locator(p_sel).first.is_visible(): 
                        page.locator(p_sel).first.click()
                        page.wait_for_timeout(500)
                except: pass

            # --- АВТО-ЛОГІН (Якщо є дані) ---
            if login and password:
                try:
                    # Шукаємо поля
                    page.fill('input[name*="login"], input[name*="user"], input[name*="email"]', login)
                    page.fill('input[type="password"]', password)
                    page.press('input[type="password"]', "Enter")
                    page.wait_for_timeout(5000)
                except Exception as e: print(f"Логін не вдався: {e}")

            # --- ПОШУК (Якщо треба) ---
            if search_query:
                try:
                    page.fill('input[name="q"], input[name="search"], input[type="search"]', search_query)
                    page.press('input[name="q"], input[name="search"], input[type="search"]', "Enter")
                    page.wait_for_timeout(3000)
                except: pass

            path = "web_result.png"
            page.screenshot(path=path, full_page=False)
            browser.close()
            return path
    except Exception as e: return None

# --- ГОЛОВНИЙ АГЕНТ (ОБРОБКА ЗАПИТІВ) ---
def ask_agent(prompt, messages_history=None):
    ua_context = (
        "Ти — OpenClaw, автономний менеджер R16.com.ua. "
        "Твоя головна задача — керувати даними та браузером. "
        "Якщо користувач пише 'онови прайси' — ти ТІЛЬКИ запускаєш функцію синхронізації, сам нічого не вигадуй. "
        "Повідомляй про початок роботи."
    )
    
    messages = [{"role": "system", "content": ua_context}]
    if messages_history: messages.extend(messages_history)
    messages.append({"role": "user", "content": prompt})
    
    # Спочатку відповідаємо користувачу (текст)
    try:
        res = requests.post(GROQ_URL, headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, 
                            json={"model": "llama-3.3-70b-versatile", "messages": messages}, timeout=20)
        bot_text = res.json()['choices'][0]['message']['content']
    except: bot_text = "Прийнято в роботу."

    status_report = ""
    
    # 1. СИНХРОНІЗАЦІЯ ПРАЙСІВ
    if "онови" in prompt.lower() and "прайс" in prompt.lower():
        status_report += "\n\n⚙️ **Запускаю процес оновлення таблиць...**\n(Це може зайняти до 30 секунд)"
        # Викликаємо Python-функцію
        res_sync = sync_tire_prices("ExcelPriceTiresNew", "R16_Pricelist")
        status_report += f"\n{res_sync}"
        
        # Надсилаємо звіт в ТГ, щоб ти точно побачив
        send_to_tg(f"Звіт по прайсах:\n{res_sync}")

    # 2. БРАУЗЕР (URL з тексту)
    url_match = re.search(r'https?://[^\s]+', prompt)
    if url_match:
        url = url_match.group(0)
        
        # Витягуємо логін/пароль якщо є
        login, password = None, None
        if "логін:" in prompt.lower():
            try: login = prompt.split("логін:")[1].split(",")[0].strip()
            except: pass
        if "пароль:" in prompt.lower():
            try: password = prompt.split("пароль:")[1].split()[0].strip()
            except: pass
            
        status_report += f"\n\n🌍 **Заходжу на сайт: {url}**"
        path = universal_browser_action(url, login, password)
        
        if path:
            tg_msg = send_to_tg(f"Скріншот сайту: {url}", path)
            status_report += f"\n📸 Скріншот надіслано в Telegram ({tg_msg})"
        else:
            status_report += "\n❌ Не вдалося зробити скріншот."

    return bot_text + status_report
