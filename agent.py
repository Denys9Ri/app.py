import os
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain_community.tools import ShellTool

# Ініціалізація моделі через GitHub
llm = ChatOpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ.get("GITHUB_TOKEN"),
    model_name="gpt-4o"
)

# Даємо агенту "руки" — ShellTool (доступ до команд Linux)
shell_tool = ShellTool()

tools = [shell_tool]

# Створюємо агента, який вміє думати і діяти
agent_executor = initialize_agent(
    tools,
    llm,
    agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True
)

def ask_agent(prompt):
    try:
        # Додаємо інструкцію, що він МОЖЕ використовувати термінал
        full_prompt = f"Ти — автономний агент OpenClaw. Якщо для відповіді на питання: '{prompt}' тобі потрібно виконати команду в терміналі — роби це негайно."
        return agent_executor.run(full_prompt)
    except Exception as e:
        return f"Помилка агента: {str(e)}"

