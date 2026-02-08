import streamlit as st
from agent import ask_agent
from PIL import Image
import io

# ... (весь CSS стиль з попередньої відповіді залишається тут)

with st.sidebar:
    st.header("🧰 Медіа")
    uploaded_photo = st.file_uploader("🖼 Фото для аналізу", type=["jpg", "png", "jpeg"])
    if uploaded_photo:
        st.image(uploaded_photo, caption="Завантажено", use_container_width=True)

# Логіка чату
if prompt := st.chat_input("Напиши команду..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        # Передаємо фото агенту, якщо воно завантажене
        image_bytes = uploaded_photo.getvalue() if uploaded_photo else None
        response = ask_agent(prompt, image_bytes)
        st.markdown(response)
    
    st.session_state.messages.append({"role": "assistant", "content": response})
