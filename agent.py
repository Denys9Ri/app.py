import os
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain_community.tools import ShellTool

# 1. Ініціалізація моделі через GitHub Models
# Переконайся, що GITHUB_TOKEN доданий у Variables на Render
llm = ChatOpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ.get("GITHUB_TOKEN"),
    model_name="gpt-4o"
)

# 2. Створюємо інструмент "Термінал" (ShellTool)
# Це дозволяє агенту виконувати команди Linux, openclaw та працювати з файлами
shell_tool = ShellTool()

# Список інструментів, які доступні агенту
tools = [shell_tool]

# 3. Створюємо Agent Executor
# handle_parsing_errors=True дозволяє агенту не падати, якщо він помилився у форматі відповіді
agent_executor = initialize_agent(
    tools,
    llm,
    agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True
)

def ask_agent(prompt):
    """Функція для обробки запитів від Streamlit інтерфейсу"""
    try:
        # Системна установка: пояснюємо агенту, що він МАЄ ПРАВО на дії
        system_instruction = (
            "Ти — автономний AI-агент OpenClaw. "
            "Твоя мета — виконувати завдання користувача, використовуючи термінал (shell_tool). "
            "Ти можеш створювати файли, перевіряти статус openclaw, запускати скрипти та аналізувати дані. "
            "Якщо завдання вимагає дії в системі — виконуй її через shell_tool без вагань. "
            f"\n\nЗавдання користувача: {prompt}"
        )
        
        # Запуск агента
        response = agent_executor.run(system_instruction)
        return response
        
    except Exception as e:
        # Якщо щось пішло не так (наприклад, не вистачило пам'яті на Render)
        return f"❌ Виникла помилка в роботі агента: {str(e)}"
