import os
import requests
import json

# ТВІЙ КЛЮЧ ЖОРСТКО В КОДІ
API_KEY = "AIzaSyALn-z6Z51QnAUh1oeqJH9JDZ-GFzR61g4"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"

def ask_agent(prompt):
    headers = {'Content-Type': 'application/json'}
    
    # Контекст для OpenClaw
    ua_context = "Ти — OpenClaw, менеджер R16.com.ua. Відповідай українською."
    
    data = {
        "contents": [{
            "parts": [{"text": f"{ua_context}\n\nЗавдання: {prompt}"}]
        }]
    }

    try:
        # Надсилаємо прямий HTTP-запит без посередників
        response = requests.post(URL, headers=headers, data=json.dumps(data), timeout=15)
        res_json = response.json()

        if response.status_code == 200:
            # Витягуємо текст відповіді
            return res_json['candidates'][0]['content']['parts'][0]['text']
        else:
            # Якщо Google знову дасть 404 або 400 - ми побачимо чисту помилку
            return f"❌ Помилка Google (Status {response.status_code}): {json.dumps(res_json)}"
            
    except Exception as e:
        return f"❌ Помилка з'єднання: {str(e)}"

# Функція для Telegram (залишаємо для майбутнього)
def send_telegram_msg(message):
    token = os.environ.get("TG_TOKEN", "")
    chat_id = os.environ.get("TG_CHAT_ID", "")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": message})
