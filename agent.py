import os
import requests
import json

# ТВІЙ НОВИЙ КЛЮЧ GROQ
GROQ_API_KEY = "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"
URL = "https://api.groq.com/openai/v1/chat/completions"

def ask_agent(prompt):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Твій контекст: ти власник, магазин R16
    ua_context = (
        "Ти — OpenClaw, автономний ШІ-менеджер магазину шин R16.com.ua. "
        "Твоя мета: допомагати клієнтам підбирати шини та займатися маркетингом. "
        "Відповідай українською мовою, будь професійним та привітним."
    )
    
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": ua_context},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(URL, headers=headers, json=data, timeout=15)
        res_json = response.json()

        if response.status_code == 200:
            # Повертаємо чисту відповідь асистента
            return res_json['choices'][0]['message']['content']
        else:
            return f"❌ Помилка Groq: {res_json.get('error', {}).get('message', 'Unknown error')}"
            
    except Exception as e:
        return f"❌ Помилка з'єднання: {str(e)}"
