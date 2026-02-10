import os
import requests
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
from langchain_community.tools import ShellTool
from langchain.agents import Tool

# 1. Ініціалізація моделі (GPT-4o-mini для швидкості та лімітів)
llm = ChatOpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ.get("GITHUB_TOKEN"),
    model_name="gpt-4o-mini"
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
    handle_parsing_errors=True
)

def ask_agent(prompt, image_data=None):
    try:
        # ПОВНА ІНСТРУКЦІЯ: ВЛАСНИЙ САЙТ + КОНКУРЕНТИ
        ua_context = (
            "Ти — провідний аналітик та адміністратор R16.com.ua.\n"
            "ТВОЇ ДОСТУПИ ДО R16:\n"
            "- Адмінка: https://r16.com.ua/admin/ (Логін: adminRia, Пароль: Baitrens!29)\n\n"
            "СТРАТЕГІЯ РОБОТИ З КОНКУРЕНТАМИ:\n"
            "1. Якщо потрібно отримати ціни з інших сайтів (infoshina, rezina.ua тощо) — використовуй Playwright через ShellTool.\n"
            "2. ЗАВЖДИ встановлюй реальний User-Agent, щоб сайти не блокували тебе як бота.\n"
            "3. Якщо сайт конкурента видає помилку або капчу — зроби скріншот, надішли його власнику і спробуй зайти через іншу сторінку.\n"
            "4. Порівнюй ціни конкурентів з цінами на R16.com.ua та пропонуй змінити ціну, якщо ми дорожчі.\n"
            "5. ЗАВЖДИ відповідай українською мовою."
        )
        
        final_input = f"{ua_context}\n\nЗавдання користувача: {prompt}"
        result = agent_executor.invoke({"input": final_input})
        return result["output"]
    except Exception as e:
        return f"❌ Помилка: {str(e)}"
