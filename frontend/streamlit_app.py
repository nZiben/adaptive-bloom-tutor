import os, requests, json, time
import streamlit as st

st.set_page_config(page_title="AI Tutor", page_icon="🎓", layout="wide")

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")

st.sidebar.title("AI-Tutor")
mode = st.sidebar.selectbox("Режим", ["exam","diagnostic"])
topic = st.sidebar.selectbox("Тема", ["linear_algebra","probability"])
student_id = st.sidebar.text_input("Student ID (опц.)","user-1")

if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "history" not in st.session_state:
    st.session_state.history = []

col1, col2 = st.columns([2,1])

with col1:
    st.header("Чат с тьютором")
    if st.session_state.session_id is None:
        if st.button("Начать сессию"):
            r = requests.post(f"{BACKEND}/api/session/start", json={"mode": mode, "topic": topic, "student_id": student_id})
            r.raise_for_status()
            data = r.json()
            st.session_state.session_id = data["session_id"]
            st.session_state.history = [{"role":"assistant","content": data["first_question"]}]
    chat_placeholder = st.container()
    with chat_placeholder:
        for m in st.session_state.history:
            if m["role"]=="assistant":
                st.markdown(f"**Тьютор:** {m['content']}")
            else:
                st.markdown(f"**Вы:** {m['content']}")

    if st.session_state.session_id:
        user_inp = st.text_input("Ваш ответ:", key="user_input")
        if st.button("Отправить") and user_inp.strip():
            st.session_state.history.append({"role":"user","content":user_inp})
            r = requests.post(f"{BACKEND}/api/session/{st.session_state.session_id}/message",
                              json={"message": user_inp})
            r.raise_for_status()
            data = r.json()
            st.session_state.history.append({"role":"assistant","content": data["reply"]})
            st.session_state.meta = data["meta"]
            st.rerun()

with col2:
    st.subheader("Статус/метрики")
    meta = st.session_state.get("meta", {})
    st.json(meta if meta else {"info":"Начните сессию"})
    if st.session_state.get("session_id"):
        if st.button("Сгенерировать отчёт"):
            r = requests.get(f"{BACKEND}/api/session/{st.session_state.session_id}/report")
            if r.ok:
                rep = r.json()
                st.image(rep["png_url"])
                st.markdown(f"[Скачать JSON-профиль]({rep['json_url']})")
        if st.button("Завершить сессию"):
            requests.post(f"{BACKEND}/api/session/{st.session_state.session_id}/complete")
            st.success("Сессия завершена")
