import os
import requests
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from playwright.sync_api import sync_playwright

# --- ЗАВАНТАЖЕННЯ КОНФІГУРАЦІЇ З RENDER ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
TG_TOKEN = os.environ.get("TG_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")
GOOGLE_CREDS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- ІНСТРУМЕНТ: ТЕЛЕГРАМ (Відправка повідомлень та фото) ---
def send_to_tg(text, file_path=None):
    if not TG_TOKEN or not TG_CHAT_ID:
        return "❌ Помилка: Ключі Telegram не налаштовані в Render"
    
    url = f"https://api.telegram.org/bot{TG_TOKEN.strip()}/"
    try:
        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                res = requests.post(url + "sendPhoto", data={"chat_id": TG_CHAT_ID.strip(), "caption": text}, files={"photo": f}, timeout=15)
        else:
            res = requests.post(url + "sendMessage", json={"chat_id": TG_CHAT_ID.strip(), "text": text}, timeout=15)
        
        return "✅ Надіслано в ТГ" if res.status_code == 200 else f"❌ Помилка ТГ: {res.text}"
    except Exception as e:
        return f"❌ Помилка зв'язку ТГ: {str(e)}"

# --- ІНСТРУМЕНТ: ГЛОБАЛЬНИЙ ПОШУК (Tavily) ---
def global_search(query):
    if not TAVILY_API_KEY:
        return "❌ Помилка: Ключ Tavily не знайдено"
    
    try:
        url = "https://api.tavily.com/search"
        data = {
            "api_key": TAVILY_API_KEY.strip(),
            "query": query,
            "search_depth": "advanced",
            "max_results": 5
        }
        res = requests.post(url, json=data, timeout=20)
        results = res.json().get("results", [])
        
        if not results:
            return "Нічого не знайдено в інтернеті."
            
        summary = "Знайдено в інтернеті:\n"
        for r in results:
            summary += f"- {r['title']}\n  URL: {r['url']}\n  Коротко: {r['content'][:200]}...\n\n"
        return summary
    except Exception as e:
        return f"❌ Помилка Tavily: {str(e)}"

# --- ІНСТРУМЕНТ: УНІВЕРСАЛЬНІ ТАБЛИЦІ (Динамічний пошук) ---
def access_any_sheet(sheet_name_query, row_data=None):
    if not GOOGLE_CREDS:
        return "❌ Помилка: JSON-ключ Google не знайдено"
    
    try:
        creds_dict = json.loads(GOOGLE_CREDS)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Отримуємо всі доступні таблиці
        all_sheets = client.openall()
        target_spreadsheet = None
        
        # Шукаємо збіг за назвою
        for s in all_sheets:
            if sheet_name_query.lower() in s.title.lower():
                target_spreadsheet = s
                break
        
        if not target_spreadsheet:
            titles = [s.title for s in all_sheets]
            return f"❌ Таблицю '{sheet_name_query}' не знайдено. Доступні: {', '.join(titles)}"
        
        worksheet = target_spreadsheet.sheet1
        if row_data:
            worksheet.append_row(row_data)
            return f"✅ Дані додано в таблицю '{target_spreadsheet.title}'"
        
        return f"✅ Таблиця '{target_spreadsheet.title}' знайдена та готова до роботи."
    except Exception as e:
        return f"❌ Помилка Google Sheets: {str(e)}"

# --- ІНСТРУМЕНТ: БРАУЗЕР (Playwright) ---
def browse_and_screenshot(url, query=None):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)
            
            if query:
                # Спроба знайти поле пошуку і ввести запит
                search_selectors = ['input[name="search"]', 'input[name="q"]', 'input[placeholder*="пошук"]', 'input[type="text"]']
                for selector in search_selectors:
                    try:
                        if page.locator(selector).is_visible():
                            page.fill(selector, query)
                            page.press(selector, "Enter")
                            page.wait_for_timeout(3000)
                            break
                    except:
                        continue
            
            path = "screenshot.png"
            page.screenshot(path=path, full_page=False)
            browser.close()
            return path
    except Exception as e:
        return None

# --- ГОЛОВНА ФУНКЦІЯ АГЕНТА ---
def ask_agent(prompt, messages_history=None):
    # Промпт для ШІ
    ua_context = (
        "Ти — OpenClaw, автономний агент для сайту R16.com.ua. "
        "Ти маєш інструменти: Tavily (глобальний пошук), Playwright (браузер) та Google Sheets. "
        "Твоє завдання: аналізувати запит користувача і виконувати дії. "
        "Якщо просять знайти ціни конкурентів — спочатку гугли, потім заходь на сайти. "
        "Якщо просять записати — шукай назву таблиці в запиті. "
        "Відповідай українською мовою."
    )
    
    full_messages = [{"role": "system", "content": ua_context}]
    if messages_history:
        for msg in messages_history:
            full_messages.append({"role": msg["role"], "content": msg["content"]})
    full_messages.append({"role": "user", "content": prompt})
    
    # Виклик Groq
    try:
        res = requests.post(
            GROQ_URL, 
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, 
            json={"model": "llama-3.3-70b-versatile", "messages": full_messages},
            timeout=25
        )
        bot_response = res.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"❌ Помилка ШІ: {str(e)}"

    # --- ЛОГІКА ВИКОНАННЯ ІНСТРУМЕНТІВ ---
    status_updates = ""
    
    # 1. Пошук та Браузер
    if any(word in prompt.lower() for word in ["знайди", "гугл", "ціни", "конкурент", "скріншот"]):
        # Глобальний пошук через Tavily
        search_info = global_search(prompt)
        status_updates += f"\n\n**Результати пошуку:**\n{search_info}"
        
        # Робимо скріншот (або твого сайту, або результату)
        target_url = "https://r16.com.ua"
        screenshot_path = browse_and_screenshot(target_url, prompt if "r16" in prompt.lower() else None)
        
        tg_status = send_to_tg(f"Звіт по запиту: {prompt}\n\n{search_info[:500]}", screenshot_path)
        status_updates += f"\n\n**Telegram:** {tg_status}"

    # 2. Робота з таблицями
    if "таблиц" in prompt.lower() or "запиши" in prompt.lower():
        # Визначаємо назву таблиці з промпту
        target_name = "R16_Pricelist" # Дефолт
        if "clean_models" in prompt.lower():
            target_name = "clean_models_for_photos_merged"
        
        # Спроба запису тестових або витягнутих даних
        sheet_res = access_any_sheet(target_name, row_data=["AI_ACTION", prompt[:50], "Виконано"])
        status_updates += f"\n\n**Google Sheets:** {sheet_res}"

    return bot_response + status_updates
