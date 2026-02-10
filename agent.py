import os
import requests
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
from langchain_community.tools import ShellTool
from langchain.agents import Tool

# 1. Ініціалізація моделі (Переходимо на Mini, щоб було більше лімітів)
llm = ChatOpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ.get("GITHUB_TOKEN"),
    model_name="gpt-4o-mini"
)

# --- ІНСТРУМЕНТ: ТЕЛЕГРАМ З ДІАГНОСТИКОЮ ---
def send_telegram_msg(message):
    token = os.environ.get("TG_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")
    
    if not token or not chat_id:
        return "Помилка: Не вказано TG_TOKEN або TG_CHAT_ID у налаштуваннях Render!"
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return "✅ Повідомлення в Telegram надіслано успішно!"
        else:
            # Виводимо конкретну помилку від Telegram для дебагу
            data = response.json()
            error_msg = data.get('description', 'Невідома помилка')
            return f"❌ Помилка Telegram API: {error_msg} (Код: {response.status_code})"
    except Exception as e:
        return f"❌ Критична помилка зв'язку: {str(e)}"

# Реєструємо інструменти
shell_tool = ShellTool()
custom_tools = [
    shell_tool,
    Tool(
        name="TelegramReporter",
        func=send_telegram_msg,
        description="Використовуй для відправки звітів та сповіщень в Telegram."
    )
]

# 2. Створення агента
prompt_template = hub.pull("hwchase17/react")
agent = create_react_agent(llm, custom_tools, prompt_template)
agent_executor = AgentExecutor(agent=agent, tools=custom_tools, verbose=True, handle_parsing_errors=True)

def ask_agent(prompt, image_data=None):
    try:
        # Додаємо контекст про Telegram в інструкцію
        system_prompt = f"Ти — агент OpenClaw. Виконуй завдання: {prompt}. Якщо треба надіслати результат — використовуй TelegramReporter."
        result = agent_executor.invoke({"input": system_prompt})
        return result["output"]
    except Exception as e:
        # Якщо знову вилетить помилка ліміту, ми це побачимо
        if "429" in str(e):
            return "🚨 Ліміти GPT-4o все ще вичерпані. Спробуй через пару годин або перевір GITHUB_TOKEN."
        return f"❌ Помилка: {str(e)}"
