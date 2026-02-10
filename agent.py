import os
import requests
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
from langchain_community.tools import ShellTool
from langchain.agents import Tool

# 1. Ініціалізація моделі
# Використовуємо gpt-4o-mini для стабільності та більших лімітів запитів
llm = ChatOpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ.get("GITHUB_TOKEN"),
    model_name="gpt-4o-mini"
)

# --- ІНСТРУМЕНТ: ТЕЛЕГРАМ СПОВІЩЕННЯ (Версія 2.0) ---
def send_telegram_msg(message):
    """Надсилає повідомлення в Telegram з автоматичним очищенням токена"""
    raw_token = os.environ.get("TG_TOKEN", "")
    token = raw_token.strip()  # Видаляємо випадкові пробіли
    
    # Видаляємо слово 'bot', якщо воно було додано випадково
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
            return "❌ Помилка 404: Telegram не знаходить бота. Перевір TG_TOKEN (має бути БЕЗ слова 'bot')."
        else:
            return f"❌ Помилка Telegram API: {response.text}"
    except Exception as e:
        return f"❌ Критична помилка зв'язку: {str(e)}"

# Реєструємо інструменти для агента
shell_tool = ShellTool()
custom_tools = [
    shell_tool,
    Tool(
        name="TelegramReporter",
        func=send_telegram_msg,
        description="Використовуй цей інструмент для відправки звітів, цін та повідомлень власнику в Telegram."
    )
]

# 2. Створення логіки агента (ReAct)
# Завантажуємо стандартний промпт з LangChain Hub
try:
    prompt_template = hub.pull("hwchase17/react")
except Exception:
    # Запасний варіант, якщо хаб недоступний
    from langchain_core.prompts import PromptTemplate
    template = """Answer the following questions as best you can. You have access to the following tools:
    {tools}
    Use the following format:
    Question: the input question you must answer
    Thought: you should always think about what to do
    Action: the action to take, should be one of [{tool_names}]
    Action Input: the input to the action
    Observation: the result of the action
    ... (this Thought/Action/Action Input/Observation can repeat N times)
    Thought: I now know the final answer
    Final Answer: the final answer to the original input question
    Begin!
    Question: {input}
    Thought:{agent_scratchpad}"""
    prompt_template = PromptTemplate.from_template(template)

# Створення виконавця
agent = create_react_agent(llm, custom_tools, prompt_template)
agent_executor = AgentExecutor(
    agent=agent, 
    tools=custom_tools, 
    verbose=True, 
    handle_parsing_errors=True
)

def ask_agent(prompt, image_data=None):
    """Головна функція для обробки запитів з інтерфейсу"""
    try:
        # Додаємо контекст для роботи
        final_input = f"Ти — автономний агент OpenClaw. Твоє завдання: {prompt}"
        if image_data:
            final_input = f"[CONTEXT: USER UPLOADED PHOTO] {final_input}"
            
        result = agent_executor.invoke({"input": final_input})
        return result["output"]
    except Exception as e:
        if "429" in str(e):
            return "🚨 Ліміти запитів GitHub вичерпані. Потрібно зачекати або змінити токен."
        return f"❌ Помилка агента: {str(e)}"
