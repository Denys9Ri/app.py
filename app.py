import streamlit as st
from agent import ask_agent

st.title("🤖 OpenClaw AI Agent")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Відображення історії чату
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Поле для введення тексту
if prompt := st.chat_input("Напишіть щось..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response = ask_agent(prompt)
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
