import os
import requests
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
from langchain_community.tools import ShellTool
from langchain.agents import Tool

# 1. Ініціалізація Gemini (Використовуємо -latest версію для стабільності)
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash-latest", # Додано -latest
    google_api_key=os.environ.get("GEMINI_API_KEY"),
    version="v1", # Примусово використовуємо стабільну версію
    temperature=0.2
)

# --- ІНСТРУМЕНТ: ТЕЛЕГРАМ ---
def send_telegram_msg(message):
    token = os.environ.get("TG_TOKEN", "").strip()
    if token.lower().startswith("bot"): token = token[3:]
    chat_id = os.environ.get("TG_CHAT_ID", "").strip()
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        return "✅ Повідомлення надіслано!" if response.status_code == 200 else f"❌ Помилка TG: {response.text}"
    except Exception as e:
        return f"❌ Помилка зв'язку: {str(e)}"

shell_tool = ShellTool()
custom_tools = [
    shell_tool,
    Tool(
        name="TelegramReporter",
        func=send_telegram_msg,
        description="Надсилає звіти, скріншоти та аналіз цін у Telegram власнику."
    )
]

# 2. Промпт та Агент
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
        # ІНСТРУКЦІЯ ДЛЯ ПЕРСОНАЛУ R16.COM.UA
        ua_context = (
            "Ти — провідний ШІ-співробітник магазину R16.com.ua. Твоє ім'я — OpenClaw.\n"
            "ДОСТУПИ ДО САЙТУ:\n"
            "- Адмінка: https://r16.com.ua/admin/ (Логін: adminRia, Пароль: Baitrens!29)\n\n"
            "ТВОЇ ЗАВДАННЯ:\n"
            "1. Моніторинг конкурентів (infoshina, rezina.ua) через Playwright.\n"
            "2. Управління адмінкою R16: перевірка замовлень та цін.\n"
            "3. ЗАВЖДИ відповідай українською мовою.\n"
            "4. Використовуй ShellTool для будь-яких технічних дій."
        )
        
        final_input = f"{ua_context}\n\nЗавдання користувача: {prompt}"
        result = agent_executor.invoke({"input": final_input})
        return result["output"]
    except Exception as e:
        return f"❌ Помилка: {str(e)}"
