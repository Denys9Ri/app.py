import os
import requests
import json

# ТВІЙ НОВИЙ КЛЮЧ
API_KEY = "AIzaSyCBYGHcVzH1kA6U1nuh27m2kYV6HS2KvQU"
# ЗМІНЮЄМО НА v1beta ТА gemini-1.5-pro
URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"

def ask_agent(prompt):
    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': API_KEY 
    }
    
    # Твій контекст для OpenClaw
    ua_context = "Ти — OpenClaw, менеджер R16.com.ua. Відповідай українською."
    
    data = {
        "contents": [{
            "parts": [{"text": f"{ua_context}\n\nЗавдання: {prompt}"}]
        }]
    }

    try:
        # Використовуємо трохи довший timeout, бо Pro версія думає глибше
        response = requests.post(URL, headers=headers, json=data, timeout=25)
        res_json = response.json()

        if response.status_code == 200:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            # Виводимо чисту причину від Google
            error_msg = res_json.get('error', {}).get('message', 'No details')
            return f"❌ Помилка Google (Status {response.status_code}): {error_msg}"
            
    except Exception as e:
        return f"❌ Помилка з'єднання: {str(e)}"
