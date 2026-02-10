import os
import requests
import json

# НОВИЙ КЛЮЧ ЖОРСТКО В КОДІ
API_KEY = "AIzaSyCBYGHcVzH1kA6U1nuh27m2kYV6HS2KvQU"
# Використовуємо стабільний шлях v1, щоб уникнути помилок 404
URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={API_KEY}"

def ask_agent(prompt):
    headers = {'Content-Type': 'application/json'}
    
    # Контекст для OpenClaw (твої доступи та назва)
    ua_context = (
        "Ти — OpenClaw, автономний менеджер R16.com.ua. "
        "Твоя адмінка: https://r16.com.ua/admin/ (adminRia / Baitrens!29). "
        "Відповідай українською мовою."
    )
    
    data = {
        "contents": [{
            "parts": [{"text": f"{ua_context}\n\nЗавдання: {prompt}"}]
        }]
    }

    try:
        response = requests.post(URL, headers=headers, data=json.dumps(data), timeout=15)
        res_json = response.json()

        if response.status_code == 200:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            # Виводимо чисту помилку від Google, якщо щось не так
            return f"❌ Помилка Google: {res_json.get('error', {}).get('message', 'Невідома помилка')}"
            
    except Exception as e:
        return f"❌ Помилка з'єднання: {str(e)}"
