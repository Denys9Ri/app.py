import os
import requests
from langchain_openai import ChatOpenAI
# Оновлений стабільний імпорт
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
from langchain_community.tools import ShellTool
from langchain.agents import Tool

# 1. Ініціалізація моделі
llm = ChatOpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ.get("GITHUB_TOKEN"),
    model_name="gpt-4o"
)

# --- Твій інструмент для Telegram ---
def send_telegram_msg(message):
    token = os.environ.get("TG_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload)
        return "Повідомлення в Telegram надіслано!" if response.status_code == 200 else f"Помилка TG: {response.text}"
    except Exception as e:
        return f"Помилка зв'язку з TG: {str(e)}"

# Реєструємо інструменти
shell_tool = ShellTool()
custom_tools = [
    shell_tool,
    Tool(
        name="TelegramReporter",
        func=send_telegram_msg,
        description="Використовуй для відправки звітів та цін власнику в Telegram."
    )
]

# 2. Створення агента за новими стандартами
# Використовуємо стандартний промпт ReAct
prompt_template = hub.pull("hwchase17/react")

# Створюємо логіку агента
agent = create_react_agent(llm, custom_tools, prompt_template)

# Створюємо виконавця (AgentExecutor)
agent_executor = AgentExecutor(
    agent=agent, 
    tools=custom_tools, 
    verbose=True, 
    handle_parsing_errors=True
)

def ask_agent(prompt, image_data=None):
    try:
        # Для GPT-4o передаємо вказівку на наявність фото
        final_input = f"[IMAGE_UPLOADED] {prompt}" if image_data else prompt
        
        # Запуск через invoke (це важливо для версії 0.3.x)
        result = agent_executor.invoke({"input": final_input})
        return result["output"]
    except Exception as e:
        return f"❌ Помилка: {str(e)}"
