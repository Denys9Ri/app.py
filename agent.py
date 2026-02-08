import os
from openai import OpenAI

# 1. Налаштовуємо клієнт для роботи з GitHub Models
client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ.get("GITHUB_TOKEN") # Ми візьмемо ключ із налаштувань сервера
)

def ask_agent(prompt):
    response = client.chat.completions.create(
        messages=[
            {
                "role": "system", 
                "content": "Ти — ШІ-агент OpenClaw. Ти допомагаєш власнику магазину шин R16.com.ua."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ],
        model="gpt-4o", # Тут можна вказати gpt-4o або Llama-3.3-70b-Instruct
        temperature=0.7,
        max_tokens=1000
    )
    
    return response.choices[0].message.content

# Перевірка
if __name__ == "__main__":
    print(ask_agent("Привіт! Хто ти?"))
