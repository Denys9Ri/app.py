import os
import requests
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from playwright.sync_api import sync_playwright

# --- КОНФІГУРАЦІЯ (Беремо з Render Environment Variables) ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
TG_TOKEN = os.environ.get("TG_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")
GOOGLE_CREDS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- ІНСТРУМЕНТ: ТЕЛЕГРАМ ---
def send_to_tg(text, file_path=None):
    if not TG_TOKEN or not TG_CHAT_ID:
        return "❌ Помилка: Ключі ТГ не встановлені"
    
    url = f"https://api.telegram.org/bot{TG_TOKEN.strip()}/"
    try:
        # Видаляємо старий файл перед відправкою, якщо він є
        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                res = requests.post(url + "sendPhoto", data={"chat_id": TG_CHAT_ID.strip(), "caption": text[:1000]}, files={"photo": f}, timeout=15)
            os.remove(file_path) # Очищуємо за собою
        else:
            res = requests.post(url + "sendMessage", json={"chat_id": TG_CHAT_ID.strip(), "text": text[:4000]}, timeout=15)
        
        return "✅ Надіслано" if res.status_code == 200 else f"❌ ТГ помилка: {res.text}"
    except Exception as e:
        return f"❌ Помилка зв'язку ТГ: {str(e)}"

# --- ІНСТРУМЕНТ: ГЛОБАЛЬНИЙ ПОШУК (Tavily) ---
def global_search(query):
    if not TAVILY_API_KEY:
        return "❌ Ключ Tavily не знайдено", None
    
    try:
        # Уточнюємо запит, щоб ШІ не шукав калькулятори
        refined_query = f"{query} купити шини ціна Україна -calculator"
        url = "https://api.tavily.com/search"
        data = {
            "api_key": TAVILY_API_KEY.strip(),
            "query": refined_query,
            "search_depth": "advanced",
            "max_results": 5
        }
        res = requests.post(url, json=data, timeout=20)
        results = res.json().get("results", [])
        
        if not results:
            return "Нічого не знайдено.", None
            
        summary = "Знайдено в мережі:\n"
        first_url = results[0]['url'] # Беремо посилання найпершого результату
        for r in results[:3]:
            summary += f"- {r['title']}\n  URL: {r['url']}\n  Інфо: {r['content'][:150]}...\n\n"
        return summary, first_url
    except Exception as e:
        return f"❌ Помилка пошуку: {str(e)}", None

# --- ІНСТРУМЕНТ: УНІВЕРСАЛЬНІ ТАБЛИЦІ ---
def access_any_sheet(sheet_name_query, row_data=None):
    if not GOOGLE_CREDS:
        return "❌ Ключ Google не знайдено"
    
    try:
        creds_dict = json.loads(GOOGLE_CREDS)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        all_sheets = client.openall()
        target = None
        # Динамічний пошук за назвою
        for s in all_sheets:
            if sheet_name_query.lower() in s.title.lower():
                target = s
                break
        
        if not target:
            return f"❌ Таблицю '{sheet_name_query}' не знайдено."
        
        if row_data:
            target.sheet1.append_row(row_data)
            return f"✅ Додано в '{target.title}'"
        return f"✅ Таблиця '{target.title}' доступна."
    except Exception as e:
        return f"❌ Помилка Таблиць: {str(e)}"

# --- ІНСТРУМЕНТ: ДИНАМІЧНИЙ БРАУЗЕР (Playwright) ---
def browse_and_screenshot(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_viewport_size({"width": 1280, "height": 800})
            page.goto(url, timeout=60000, wait_until="networkidle")
            
            path = "web_capture.png"
            page.screenshot(path=path)
            browser.close()
            return path
    except Exception as e:
        return None

# --- ГОЛОВНА ЛОГІКА АГЕНТА ---
def ask_agent(prompt, messages_history=None):
    ua_context = (
        "Ти — Суперагент OpenClaw для R16.com.ua. Ти дієш автономно. "
        "Твої інструменти: Tavily (пошук), Playwright (скріншоти) та Google Sheets. "
        "Якщо тебе просять знайти ціни — спочатку використовуй пошук, потім зроби скріншот ЗНАЙДЕНОГО сайту. "
        "Завжди пиши в ту таблицю, яку вказав користувач."
    )
    
    full_messages = [{"role": "system", "content": ua_context}]
    if messages_history:
        for msg in messages_history:
            full_messages.append({"role": msg["role"], "content": msg["content"]})
    full_messages.append({"role": "user", "content": prompt})
    
    try:
        res = requests.post(
            GROQ_URL, 
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, 
            json={"model": "llama-3.3-70b-versatile", "messages": full_messages},
            timeout=25
        )
        bot_text = res.json()['choices'][0]['message']['content']
    except Exception as e:
        bot_text = f"Помилка ШІ: {str(e)}"

    # --- ВИКОНАННЯ ДІЙ ---
    status_updates = ""

    # 1. Пошук та Динамічний скріншот
    if any(word in prompt.lower() for word in ["знайди", "ціни", "конкурент", "гугл", "скріншот"]):
        search_data, found_url = global_search(prompt)
        status_updates += f"\n\n**Аналіз ринку:**\n{search_data}"
        
        # Визначаємо, який сайт фоткати: знайдений або r16 (якщо пошук не вдався)
        target_to_screenshot = found_url if found_url else "https://r16.com.ua"
        screenshot_path = browse_and_screenshot(target_to_screenshot)
        
        tg_status = send_to_tg(f"Звіт OpenClaw:\n{prompt}\n\nДжерело: {target_to_screenshot}", screenshot_path)
        status_updates += f"\n\n**Telegram:** {tg_status}"

    # 2. Робота з таблицями
    if "таблиц" in prompt.lower() or "запиши" in prompt.lower():
        target_sheet = "R16_Pricelist"
        if "clean_models" in prompt.lower():
            target_sheet = "clean_models_for_photos_merged"
        
        sheet_res = access_any_sheet(target_sheet, row_data=["AI_ACTION", prompt[:100], "Виконано"])
        status_updates += f"\n\n**Google Sheets:** {sheet_res}"

    return bot_text + status_updates
