import os
import requests
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent
from langchain.agents.agent_executor import AgentExecutor
from langchain import hub
from langchain_community.tools import ShellTool
from langchain.agents import Tool

# 1. Ініціалізація моделі
llm = ChatOpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ.get("GITHUB_TOKEN"),
    model_name="gpt-4o"
)

# --- ІНСТРУМЕНТ: ТЕЛЕГРАМ СПОВІЩЕННЯ ---
def send_telegram_msg(message):
    """Надсилає звіт або повідомлення в Telegram"""
    token = os.environ.get("TG_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return "Повідомлення в Telegram надіслано успішно!"
        else:
            return f"Помилка TG: {response.text}"
    except Exception as e:
        return f"Помилка зв'язку з TG: {str(e)}"

# Реєструємо інструменти
shell_tool = ShellTool()
custom_tools = [
    shell_tool,
    Tool(
        name="TelegramReporter",
        func=send_telegram_msg,
        description="Використовуй цей інструмент, щоб надіслати власнику важливу інформацію, звіти або ціни в Telegram."
    )
]

# Створення агента
prompt_template = hub.pull("hwchase17/react")
agent = create_react_agent(llm, custom_tools, prompt_template)
agent_executor = AgentExecutor(agent=agent, tools=custom_tools, verbose=True, handle_parsing_errors=True)

def ask_agent(prompt, image_data=None):
    try:
        final_input = f"[IMAGE_UPLOADED] {prompt}" if image_data else prompt
        result = agent_executor.invoke({"input": final_input})
        return result["output"]
    except Exception as e:
        return f"❌ Помилка: {str(e)}"
