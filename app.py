import streamlit as st
from agent import ask_agent

# 1. Налаштування сторінки (Мобільний вигляд)
st.set_page_config(
    page_title="OpenClaw Mobile",
    page_icon="🤖",
    layout="centered"
)

# 2. Стилізація під "Матове скло" та темну тему
st.markdown("""
    <style>
    /* Основний фон */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    }
    
    /* Ефект скла для повідомлень */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(10px);
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 10px;
        padding: 10px;
    }

    /* Адаптація під мобільні пристрої */
    @media (max-width: 640px) {
        .stChatMessage {
            padding: 8px;
            font-size: 14px;
        }
    }

    /* Стилізація кнопок */
    .stButton > button {
        background: rgba(255, 255, 255, 0.1);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.2);
        backdrop-filter: blur(5px);
        width: 100%;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 OpenClaw Agent")
st.caption("Mobile Glass Edition | AutoTalk UA")

# 3. Бічна панель для медіа та функцій
with st.sidebar:
    st.header("🧰 Інструменти")
    
    # Кнопки завантаження
    uploaded_photo = st.file_uploader("🖼 Завантажити фото", type=["jpg", "png", "jpeg"])
    uploaded_video = st.file_uploader("🎥 Завантажити відео", type=["mp4", "mov"])
    
    # Голосовий ввод (імітація для веб-інтерфейсу)
    if st.button("🎤 Голосовий ввод (ON/OFF)"):
        st.info("Голосовий ввод активується через браузерний мікрофон...")

# 4. Логіка чату
if "messages" not in st.session_state:
    st.session_state.messages = []

# Відображення повідомлень
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Поле вводу
if prompt := st.chat_input("Напиши команду для лобстера..."):
    # Додаємо повідомлення користувача
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Відповідь агента
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = ask_agent(prompt)
            st.markdown(response)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
