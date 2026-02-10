import os
import requests
from google import genai
# Спробуємо імпортувати ShellTool так, щоб він не викликав помилку відразу
try:
    from langchain_community.tools import ShellTool
except ImportError:
    ShellTool = None

# 1. ПРЯМЕ ПІДКЛЮЧЕННЯ (Оминаємо глюки LangChain)
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Ініціалізація інструмента
if ShellTool:
    shell_tool = ShellTool()
else:
    shell_tool = None

# --- ІНСТРУМЕНТ: ТЕЛЕГРАМ ---
def send_telegram_msg(message):
    token = os.environ.get("TG_TOKEN", "").strip()
    chat_id = os.environ.get("TG_CHAT_ID", "").strip()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)
        return "✅ Надіслано"
    except:
        return "❌ Помилка"

# 2. ОСНОВНА ФУНКЦІЯ
def ask_agent(prompt):
    try:
        ua_context = "Ти OpenClaw, менеджер R16.com.ua. Відповідай українською."
        
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=f"{ua_context}\n\nЗавдання: {prompt}"
        )
        return response.text
    except Exception as e:
        return f"❌ Помилка API: {str(e)}"
