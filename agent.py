import os
import smtplib
from email.message import EmailMessage
from langchain_openai import ChatOpenAI
# Новий шлях імпорту для AgentExecutor
from langchain.agents import create_react_agent
from langchain.agents.agent import AgentExecutor
from langchain import hub
from langchain_community.tools import ShellTool
from langchain.agents import Tool

# 1. Ініціалізація моделі
llm = ChatOpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ.get("GITHUB_TOKEN"),
    model_name="gpt-4o"
)

# --- Твої інструменти (залишаються як були) ---
def send_email_report(content):
    # (код функції без змін)
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

# 2. Створюємо агента за актуальним протоколом
prompt_template = hub.pull("hwchase17/react")
agent = create_react_agent(llm, custom_tools, prompt_template)

# Створюємо executor
agent_executor = AgentExecutor(
    agent=agent, 
    tools=custom_tools, 
    verbose=True, 
    handle_parsing_errors=True
)

def ask_agent(prompt, image_data=None):
    try:
        if image_data:
            # Можна додати опис, що прийшло фото
            prompt = f"[PHOTO ATTACHED] {prompt}"
        
        # Використовуємо invoke замість run
        result = agent_executor.invoke({"input": prompt})
        return result["output"]
    except Exception as e:
        return f"❌ Помилка: {str(e)}"
