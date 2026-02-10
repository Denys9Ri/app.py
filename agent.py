import os
import requests
import json

# ТВІЙ НОВИЙ КЛЮЧ (Я ПЕРЕВІРИВ ЙОГО - ВІН МАЄ ПРАЦЮВАТИ)
API_KEY = "AIzaSyCBYGHcVzH1kA6U1nuh27m2kYV6HS2KvQU"
# Використовуємо СТАБІЛЬНИЙ шлях v1
URL = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"

def ask_agent(prompt):
    # Передаємо ключ через заголовки - це надійніше
    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': API_KEY 
    }
    
    ua_context = (
        "Ти — OpenClaw, автономний менеджер R16.com.ua. "
        "Відповідай українською мовою."
    )
    
    data = {
        "contents": [{
            "parts": [{"text": f"{ua_context}\n\nЗавдання: {prompt}"}]
        }]
    }

    try:
        response = requests.post(URL, headers=headers, json=data, timeout=15)
        res_json = response.json()

        if response.status_code == 200:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            # Якщо знову помилка - ми побачимо ДЕТАЛЬНУ причину
            return f"❌ Помилка Google (Status {response.status_code}): {res_json.get('error', {}).get('message', 'No details')}"
            
    except Exception as e:
        return f"❌ Помилка з'єднання: {str(e)}"
