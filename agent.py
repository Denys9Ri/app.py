import os
import re
import requests
import json
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

# --- ДОДАТКОВО: Функція витягування URL з тексту ---
def extract_url_from_text(text):
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, text)
    return urls[0] if urls else None

# --- ІНСТРУМЕНТ: ТЕЛЕГРАМ ---
def send_to_tg(text, file_path=None):
    if not TG_TOKEN or not TG_CHAT_ID: return "❌ Помилка: Немає ключів ТГ"
    url = f"https://api.telegram.org/bot{TG_TOKEN.strip()}/"
    try:
        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                requests.post(url + "sendPhoto", data={"chat_id": TG_CHAT_ID.strip(), "caption": text[:1000]}, files={"photo": f}, timeout=20)
            os.remove(file_path)
        else:
            requests.post(url + "sendMessage", json={"chat_id": TG_CHAT_ID.strip(), "text": text[:4000]}, timeout=15)
        return "✅ Надіслано"
    except Exception as e: return f"❌ Помилка ТГ: {str(e)}"

# --- ІНСТРУМЕНТ: ПОШУК (Tavily) ---
def global_search(query):
    if not TAVILY_API_KEY: return "❌ Немає ключа Tavily", None
    try:
        refined_query = f"{query} ціна купити україна -calculator"
        res = requests.post("https://api.tavily.com/search", json={"api_key": TAVILY_API_KEY.strip(), "query": refined_query, "search_depth": "advanced"}, timeout=20)
        results = res.json().get("results", [])
        if not results: return "Пусто.", None
        summary = "\n".join([f"- {r['title']} ({r['url']}): {r['content'][:150]}..." for r in results[:3]])
        return summary, results[0]['url']
    except Exception as e: return f"Помилка пошуку: {e}", None

# --- ІНСТРУМЕНТ: БРАУЗЕР ---
def browse_and_screenshot(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            # Маскуємось під звичайного користувача
            page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            page.goto(url, timeout=90000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000) # Чекаємо дозавантаження фото
            path = "web_capture.png"
            page.screenshot(path=path, full_page=False)
            browser.close()
            return path
    except Exception as e: return None

# --- ІНСТРУМЕНТ: ТАБЛИЦІ ---
def access_any_sheet(sheet_query, row_data=None):
    if not GOOGLE_CREDS: return "❌ Немає ключа Google"
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(GOOGLE_CREDS), ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        client = gspread.authorize(creds)
        all_sheets = client.openall()
        target = next((s for s in all_sheets if sheet_query.lower() in s.title.lower()), None)
        if not target: return "❌ Таблицю не знайдено"
        if row_data:
            target.sheet1.append_row(row_data)
            return f"✅ Додано в '{target.title}'"
        return f"✅ Таблиця '{target.title}' знайдена"
    except Exception as e: return f"❌ Помилка Google: {e}"

# --- ГОЛОВНИЙ МОЗОК ---
def ask_agent(prompt, messages_history=None):
    ua_context = (
        "Ти — OpenClaw, автономний бізнес-асистент. "
        "Ти вмієш бачити інтернет, читати таблиці і надсилати файли в Telegram. "
        "Твоє завдання: виконати команду і прозвітувати. "
        "Ніколи не кажи 'я не можу відправити скріншот', бо це робить Python-код після твоєї відповіді."
    )
    
    # 1. Запит до ШІ
    full_messages = [{"role": "system", "content": ua_context}]
    if messages_history:
        for msg in messages_history: full_messages.append(msg)
    full_messages.append({"role": "user", "content": prompt})
    
    try:
        res = requests.post(GROQ_URL, headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, json={"model": "llama-3.3-70b-versatile", "messages": full_messages}, timeout=25)
        bot_text = res.json()['choices'][0]['message']['content']
    except Exception as e: bot_text = f"Помилка ШІ: {str(e)}"

    status = ""
    
    # 2. Логіка виконання дій
    # А. Перевіряємо, чи є пряме посилання в тексті
    direct_url = extract_url_from_text(prompt)
    
    if direct_url:
        # Якщо є посилання - йдемо прямо туди
        path = browse_and_screenshot(direct_url)
        tg_res = send_to_tg(f"Скріншот за посиланням: {direct_url}", path)
        status += f"\n\n**[Посилання оброблено]** Telegram: {tg_res}"
        
    elif any(w in prompt.lower() for w in ["знайди", "гугл", "ціни", "конкурент"]):
        # Якщо посилання немає - гуглимо
        search_txt, found_url = global_search(prompt)
        status += f"\n\n**[Пошук]** {search_txt[:200]}..."
        if found_url:
            path = browse_and_screenshot(found_url)
            tg_res = send_to_tg(f"Результат пошуку: {prompt}\nURL: {found_url}", path)
            status += f"\nTelegram: {tg_res}"

    if "таблиц" in prompt.lower() or "запиши" in prompt.lower():
        t_name = "clean_models_for_photos_merged" if "clean" in prompt.lower() else "R16_Pricelist"
        res = access_any_sheet(t_name, ["AI_LOG", prompt, "Auto-Add"])
        status += f"\n\n**[Таблиця]** {res}"

    return bot_text + status
