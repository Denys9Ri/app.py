import os
import smtplib
from email.message import EmailMessage
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub
from langchain_community.tools import ShellTool
from langchain.agents import Tool

# 1. Ініціалізація моделі
llm = ChatOpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ.get("GITHUB_TOKEN"),
    model_name="gpt-4o"
)

# --- Твої інструменти (залишаються без змін) ---
def send_email_report(content):
    # (код функції send_email_report такий самий, як раніше)
    pass

shell_tool = ShellTool()
custom_tools = [
    shell_tool,
    Tool(
        name="SendEmailReport",
        func=send_email_report,
        description="Використовуй для відправки звітів або результатів аналізу на email."
    )
]

# 2. НОВИЙ СПОСІБ СТВОРЕННЯ АГЕНТА (LangChain 0.3+)
# Отримуємо стандартний промпт для ReAct агента з хабу
prompt_template = hub.pull("hwchase17/react")

# Створюємо агента через новий метод
agent = create_react_agent(llm, custom_tools, prompt_template)

# Створюємо об'єкт для виконання (executor)
agent_executor = AgentExecutor(
    agent=agent, 
    tools=custom_tools, 
    verbose=True, 
    handle_parsing_errors=True
)

def ask_agent(prompt, image_data=None):
    try:
        if image_data:
            prompt = f"[КОРИСТУВАЧ ЗАВАНТАЖИВ ФОТО]. Завдання: {prompt}"
        
        # Виклик агента тепер через invoke
        result = agent_executor.invoke({"input": prompt})
        return result["output"]
    except Exception as e:
        return f"❌ Помилка: {str(e)}"
