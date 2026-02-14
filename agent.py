import requests
import json

GROQ_API_KEY = "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"
URL = "https://api.groq.com/openai/v1/chat/completions"

# Додаємо параметр messages_history
def ask_agent(prompt, messages_history=None):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    ua_context = (
        "Ти — OpenClaw, автономний менеджер магазину R16.com.ua. "
        "Ти пам'ятаєш деталі розмови. Якщо клієнт каже 'Зима', "
        "ти маєш пам'ятати, яке в нього авто, якщо він казав це раніше."
    )
    
    # Формуємо список повідомлень для Groq
    full_messages = [{"role": "system", "content": ua_context}]
    
    # Якщо історія є, додаємо її в запит
    if messages_history:
        for msg in messages_history:
            role = "user" if msg["role"] == "user" else "assistant"
            full_messages.append({"role": role, "content": msg["content"]})
    
    # Додаємо поточне повідомлення
    full_messages.append({"role": "user", "content": prompt})
    
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": full_messages,
        "temperature": 0.7
    }

    try:
        response = requests.post(URL, headers=headers, json=data, timeout=15)
        res_json = response.json()
        if response.status_code == 200:
            return res_json['choices'][0]['message']['content']
        else:
            return f"❌ Помилка: {res_json.get('error', {}).get('message', 'error')}"
    except Exception as e:
        return f"❌ З'єднання: {str(e)}"
