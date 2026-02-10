import os
import requests
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
from langchain_community.tools import ShellTool
from langchain.agents import Tool

# 1. Ініціалізація СТАБІЛЬНОЇ моделі Gemini 1.5 Flash
# Вона доступна у всіх регіонах і не видає 404
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=os.environ.get("GEMINI_API_KEY"),
    temperature=0.1
)

# 2. Налаштування інструментів
shell_tool = ShellTool()

def send_telegram_msg(message):
    token = os.environ.get("TG_TOKEN", "").strip()
    if token.lower().startswith("bot"): token = token[3:]
    chat_id = os.environ.get("TG_CHAT_ID", "").strip()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        return "✅ Надіслано!" if response.status_code == 200 else f"❌ Помилка TG"
    except:
        return "❌ Помилка зв'язку"

custom_tools = [
    shell_tool,
    Tool(
        name="TelegramReporter",
        func=send_telegram_msg,
        description="Надсилає звіти та аналіз в Telegram власнику R16.com.ua."
    )
]

# 3. Створення Агента
prompt_template = hub.pull("hwchase17/react")
agent = create_react_agent(llm, custom_tools, prompt_template)
agent_executor = AgentExecutor(
    agent=agent, 
    tools=custom_tools, 
    verbose=True, 
    handle_parsing_errors=True,
    max_iterations=10
)

def ask_agent(prompt):
    try:
        ua_context = (
            "Ти — OpenClaw, автономний менеджер R16.com.ua. "
            "Доступи: https://r16.com.ua/admin/ (adminRia / Baitrens!29). "
            "ЗАВЖДИ відповідай українською. Використовуй ShellTool для Playwright."
        )
        final_input = f"{ua_context}\n\nЗавдання: {prompt}"
        result = agent_executor.invoke({"input": final_input})
        return result["output"]
    except Exception as e:
        # Якщо знову 404, виводимо зрозумілу причину
        if "404" in str(e):
            return "❌ Помилка доступу до моделі. Спробуйте створити НОВИЙ API ключ у Google AI Studio."
        return f"❌ Помилка: {str(e)}"
