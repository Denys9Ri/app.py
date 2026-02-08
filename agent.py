import os
import smtplib
from email.message import EmailMessage
from langchain_openai import ChatOpenAI
# Ми імпортуємо тільки те, що на 100% стабільно
import langchain.agents as agents
from langchain_community.tools import ShellTool
from langchain.agents import Tool, create_react_agent
from langchain import hub

# 1. Ініціалізація моделі
llm = ChatOpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ.get("GITHUB_TOKEN"),
    model_name="gpt-4o"
)

# --- Інструменти ---
def send_email_report(content):
    # Твій SMTP код залишається таким самим
    return "Лист відправлено"

shell_tool = ShellTool()
custom_tools = [
    shell_tool,
    Tool(
        name="SendEmailReport",
        func=send_email_report,
        description="Використовуй для відправки звітів."
    )
]

# 2. Створення виконавця через універсальний клас
# У нових версіях AgentExecutor доступний прямо так:
from langchain.agents import AgentExecutor

prompt_template = hub.pull("hwchase17/react")
agent = create_react_agent(llm, custom_tools, prompt_template)

# Цей об'єкт — це "мозок", що керує терміналом і поштою
agent_executor = AgentExecutor(
    agent=agent, 
    tools=custom_tools, 
    verbose=True, 
    handle_parsing_errors=True
)

def ask_agent(prompt, image_data=None):
    try:
        # Для мобільної версії з фото
        user_input = f"[UPLOADED_FILE] {prompt}" if image_data else prompt
        
        # Використовуємо .invoke — це стандарт 2025-2026 років
        result = agent_executor.invoke({"input": user_input})
        return result["output"]
    except Exception as e:
        return f"❌ Помилка: {str(e)}"
