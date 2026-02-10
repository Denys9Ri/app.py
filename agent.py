import os
import requests
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
from langchain_community.tools import ShellTool
from langchain.agents import Tool

# 1. Ініціалізація моделі (GPT-4o-mini для стабільності)
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
        description="Використовуй для відправки звітів та скріншотів власнику в Telegram."
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
        # Жорстка інструкція українською мовою
        ua_context = (
            "Ти — професійний асистент OpenClaw для магазину шин R16.com.ua. "
            "Твоє завдання — допомагати власнику. "
            "ЗАВЖДИ відповідай українською мовою. "
            "Використовуй ShellTool для запуску скриптів Playwright без вагань. "
        )
        
        final_input = f"{ua_context}\n\nЗавдання користувача: {prompt}"
        result = agent_executor.invoke({"input": final_input})
        return result["output"]
    except Exception as e:
        return f"❌ Помилка: {str(e)}"
