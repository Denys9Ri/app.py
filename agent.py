import os
import requests
from google import genai
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
from langchain_community.tools import ShellTool
from langchain.agents import Tool

# 1. Новий спосіб ініціалізації (Google GenAI SDK)
# Це зніме проблему 404 і v1beta
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Обгортка для LangChain, щоб він розумів нову бібліотеку
def call_gemini(prompt):
    response = client.models.generate_content(
        model="gemini-1.5-flash", 
        contents=prompt
    )
    return response.text

# 2. Інструменти
shell_tool = ShellTool()

def send_telegram_msg(message):
    token = os.environ.get("TG_TOKEN", "").strip()
    chat_id = os.environ.get("TG_CHAT_ID", "").strip()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)
        return "✅ Повідомлення надіслано"
    except:
        return "❌ Помилка зв'язку"

custom_tools = [
    shell_tool,
    Tool(
        name="TelegramReporter",
        func=send_telegram_msg,
        description="Звіти в Telegram для R16.com.ua."
    )
]

# 3. Функція для зв'язку з асистент-панеллю
def ask_agent(prompt):
    try:
        # Контекст для OpenClaw
        ua_context = (
            "Ти — OpenClaw, автономний менеджер R16.com.ua. "
            "Відповідай українською. Використовуй інструменти для роботи."
        )
        # Використовуємо прямий виклик через новий SDK
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=f"{ua_context}\n\nЗавдання: {prompt}"
        )
        return response.text
    except Exception as e:
        return f"❌ Помилка: {str(e)}"
