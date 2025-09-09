import os
import requests
import streamlit as st

st.set_page_config(page_title="AI Tutor — Тестбенч", page_icon="🧪", layout="wide")
BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")


def api_post(path, json_body):
    token = st.session_state.get("token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = requests.post(f"{BACKEND}{path}", json=json_body, headers=headers)
    if not r.ok:
        st.error(f"API error {r.status_code}: {r.text}")
        r.raise_for_status()
    return r


st.title("🧪 Тестбенч")
topic = st.selectbox("Тема", ["linear_algebra", "probability"])
with st.form("tb_form"):
    c1_q = st.text_area("Вопрос 1", value="Explain why matrix multiplication is not commutative.")
    c1_a = st.text_area("Эталонный ответ 1", value="Provide counterexample AB != BA with 2x2 matrices.")
    submitted = st.form_submit_button("Запустить")
    if submitted:
        out = api_post(
            "/api/testbench/run",
            {"topic": topic, "cases": [{"question": c1_q, "ideal_answer": c1_a}]},
        ).json()
        st.subheader("Результаты")
        st.json(out)
