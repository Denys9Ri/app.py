import streamlit as st
from agent import ask_agent
import base64

# Налаштування сторінки
st.set_page_config(page_title="R16 AI Assistant", page_icon="🤖", layout="wide")

# Стилізація під Gemini (чистий та сучасний дизайн)
st.markdown("""
    <style>
    /* Головний фон */
    .stApp {
        background-color: #131314;
        color: #e3e3e3;
    }
    
    /* Контейнер для чату */
    .chat-container {
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
    }

    /* Повідомлення користувача */
    .user-msg {
        background-color: #2b2a2b;
        padding: 15px 20px;
        border-radius: 20px;
        margin-bottom: 20px;
        border: 1px solid #444;
        font-size: 1.1rem;
        line-height: 1.5;
    }

    /* Повідомлення бота (Gemini Style) */
    .bot-msg {
        background-color: transparent;
        padding: 15px 5px;
        margin-bottom: 30px;
        font-size: 1.1rem;
        line-height: 1.6;
        display: flex;
        gap: 15px;
    }

    /* Аватарки або іконки */
    .bot-icon {
        width: 35px;
        height: 35px;
        background: linear_gradient(45deg, #4285f4, #9b72cb);
        border-radius: 50%;
        flex-shrink: 0;
    }

    /* Поле введення */
    .stTextInput input {
        background-color: #1e1f20 !important;
        color: white !important;
        border: 1px solid #5f6368 !important;
        border-radius: 30px !important;
        padding: 15px 25px !important;
    }

    /* Заголовок */
    h1 {
        font-family: 'Google Sans', sans-serif;
        font-weight: 500;
        text-align: center;
        color: #ffffff;
        margin-bottom: 40px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("R16 AI Асистент")

# Ініціалізація історії чату
if "messages" not in st.session_state:
    st.session_state.messages = []

# Вивід історії чату
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(f'<div class="user-msg"><b>Ви:</b><br>{message["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'''
            <div class="bot-msg">
                <div class="bot-icon"></div>
                <div>{message["content"]}</div>
            </div>
        ''', unsafe_allow_html=True)

# Поле для введення тексту
user_input = st.chat_input("Запитайте щось у R16 Асистента...")

if user_input:
    # Додаємо повідомлення користувача в історію
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.markdown(f'<div class="user-msg"><b>Ви:</b><br>{user_input}</div>', unsafe_allow_html=True)
    
    with st.spinner('Агент думає...'):
        # Отримуємо відповідь від агента (вже українською мовою)
        response = ask_agent(user_input)
        
        # Додаємо відповідь бота
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.markdown(f'''
            <div class="bot-msg">
                <div class="bot-icon"></div>
                <div>{response}</div>
            </div>
        ''', unsafe_allow_html=True)
