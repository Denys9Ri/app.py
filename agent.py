import os
import requests
from google import genai
from langchain_community.tools import ShellTool
from langchain.agents import Tool

# 1. ПРЯМЕ ПІДКЛЮЧЕННЯ (Оминаємо глюки LangChain)
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

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

shell_tool = ShellTool()
custom_tools = [
    shell_tool,
    Tool(
        name="TelegramReporter",
        func=send_telegram_msg,
        description="Звіти в Telegram для R16."
    )
]

# 2. ОСНОВНА ФУНКЦІЯ (Вона тепер не видасть 404)
def ask_agent(prompt):
    try:
        ua_context = (
            "Ти — OpenClaw, автономний менеджер R16.com.ua. "
            "Відповідай українською мовою. Твоє завдання — партизанський маркетинг."
        )
        
        # Прямий виклик через новий SDK Google
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=f"{ua_context}\n\nЗавдання: {prompt}"
        )
        return response.text
    except Exception as e:
        return f"❌ Помилка API: {str(e)}"
