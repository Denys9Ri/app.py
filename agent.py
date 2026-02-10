import os
import requests
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
from langchain_community.tools import ShellTool
from langchain.agents import Tool

# 1. Ініціалізація Gemini (Використовуємо стабільний підхід)
# Ми прибираємо параметр version і залишаємо тільки модель та ключ
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash", 
    google_api_key=os.environ.get("GEMINI_API_KEY"),
    temperature=0.1 # Зменшуємо для точності в адмінці та цінах
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
        return "✅ Надіслано!" if response.status_code == 200 else f"❌ Помилка: {response.text}"
    except Exception as e:
        return f"❌ Помилка зв'язку: {str(e)}"

shell_tool = ShellTool()
custom_tools = [
    shell_tool,
    Tool(
        name="TelegramReporter",
        func=send_telegram_msg,
        description="Надсилає звіти та скріншоти в Telegram власнику R16."
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
    max_iterations=12 # Даємо більше часу на роздуми
)

def ask_agent(prompt):
    try:
        # ІНСТРУКЦІЯ В СТИЛІ OPENCLAW ДЛЯ R16
        ua_context = (
            "Ти — автономний агент OpenClaw для магазину R16.com.ua. "
            "Твої дані: Адмінка https://r16.com.ua/admin/ (adminRia / Baitrens!29).\n"
            "ТВОЯ СТРАТЕГІЯ:\n"
            "1. Якщо не бачиш модель, спробуй перевірити доступ через ShellTool.\n"
            "2. Використовуй Playwright для аналізу цін (infoshina, rezina.ua).\n"
            "3. ЗАВЖДИ відповідай українською мовою.\n"
            "4. Якщо завдання складне — розбий його на кроки: зайти, знайти, звітувати."
        )
        
        final_input = f"{ua_context}\n\nЗавдання: {prompt}"
        result = agent_executor.invoke({"input": final_input})
        return result["output"]
    except Exception as e:
        # Якщо знову 404, виводимо зрозумілу пораду
        if "404" in str(e):
            return "❌ Помилка 404: Модель не знайдена. Перевір, чи вірний GEMINI_API_KEY у Render."
        return f"❌ Помилка: {str(e)}"
