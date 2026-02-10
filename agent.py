import os
import requests
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
from langchain_community.tools import ShellTool
from langchain.agents import Tool

# 1. Ініціалізація моделі
# Використовуємо gpt-4o-mini для більшої кількості запитів на добу
llm = ChatOpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ.get("GITHUB_TOKEN"),
    model_name="gpt-4o-mini"
)

# --- ІНСТРУМЕНТ: ТЕЛЕГРАМ СПОВІЩЕННЯ ---
def send_telegram_msg(message):
    """Надсилає повідомлення в Telegram з очищенням токена від помилок"""
    raw_token = os.environ.get("TG_TOKEN", "")
    token = raw_token.strip()  # Видаляємо пробіли на початку та в кінці
    
    # Видаляємо слово 'bot', якщо воно було додано у Render випадково
    if token.lower().startswith("bot"):
        token = token[3:]
        
    chat_id = os.environ.get("TG_CHAT_ID", "").strip()
    
    if not token or not chat_id:
        return "❌ Помилка: В Render не налаштовані змінні TG_TOKEN або TG_CHAT_ID."

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": message, 
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return "✅ Повідомлення в Telegram надіслано успішно!"
        elif response.status_code == 404:
            return "❌ Помилка 404: Бот не знайдений. Перевірте токен у Render."
        else:
            return f"❌ Помилка API: {response.text}"
    except Exception as e:
        return f"❌ Критична помилка зв'язку: {str(e)}"

# Реєструємо інструменти
shell_tool = ShellTool()
custom_tools = [
    shell_tool,
    Tool(
        name="TelegramReporter",
        func=send_telegram_msg,
        description="Використовуй для відправки звітів та повідомлень власнику в Telegram."
    )
]

# 2. Створення логіки агента
prompt_template = hub.pull("hwchase17/react")
agent = create_react_agent(llm, custom_tools, prompt_template)
agent_executor = AgentExecutor(
    agent=agent, 
    tools=custom_tools, 
    verbose=True, 
    handle_parsing_errors=True
)

def ask_agent(prompt, image_data=None):
    """Обробка запитів з інтерфейсу"""
    try:
        final_input = f"Ти — автономний агент OpenClaw. Виконай: {prompt}"
        if image_data:
            final_input = f"[CONTEXT: PHOTO UPLOADED] {final_input}"
            
        result = agent_executor.invoke({"input": final_input})
        return result["output"]
    except Exception as e:
        if "429" in str(e):
            return "🚨 Ліміти запитів GitHub вичерпані. Потрібно зачекати."
        return f"❌ Помилка агента: {str(e)}"
