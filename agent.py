import os
import requests
import json

API_KEY = "AIzaSyCBYGHcVzH1kA6U1nuh27m2kYV6HS2KvQU"
# ПЕРЕМИКАЄМОСЯ НА PRO ВЕРСІЮ ТА V1BETA
URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"

def ask_agent(prompt):
    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': API_KEY 
    }
    
    data = {
        "contents": [{
            "parts": [{"text": f"Ти OpenClaw, менеджер R16.com.ua. Відповідай українською.\n\nЗавдання: {prompt}"}]
        }]
    }

    try:
        response = requests.post(URL, headers=headers, json=data, timeout=20)
        res_json = response.json()

        if response.status_code == 200:
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"❌ Спробуймо іншу модель. Помилка: {res_json.get('error', {}).get('message', 'No details')}"
            
    except Exception as e:
        return f"❌ Помилка з'єднання: {str(e)}"
