import os
import requests
import streamlit as st

st.set_page_config(page_title="AI Tutor — Администрирование", page_icon="🛠️", layout="wide")
BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")


def api_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def api_post(path, json_body):
    r = requests.post(f"{BACKEND}{path}", json=json_body, headers=api_headers())
    if not r.ok:
        try:
            st.error(f"API error {r.status_code}: {r.json().get('detail')}")
        except Exception:
            st.error(f"API error {r.status_code}: {r.text}")
        r.raise_for_status()
    return r


def api_get(path):
    r = requests.get(f"{BACKEND}{path}", headers=api_headers())
    if not r.ok:
        try:
            st.error(f"API error {r.status_code}: {r.json().get('detail')}")
        except Exception:
            st.error(f"API error {r.status_code}: {r.text}")
        r.raise_for_status()
    return r


st.title("🛠️ Администрирование")

if "token" not in st.session_state or not st.session_state.token:
    st.warning("Сначала войдите в систему (как администратор).")
    st.stop()

me = api_get("/api/me").json()
if me.get("role") != "admin":
    st.error("Доступ только для администраторов.")
    st.stop()

st.success(f"Вы вошли как администратор: {me['username']}")

st.header("Темы")
with st.form("create_topic"):
    name = st.text_input("Название новой темы", placeholder="например, linear_algebra_ext")
    submitted = st.form_submit_button("Создать тему")
    if submitted and name.strip():
        t = api_post("/api/admin/topics", {"name": name.strip()}).json()
        st.success(f"Тема создана: {t['name']} (вопросов: {t['question_count']})")

topics = api_get("/api/topics").json()
if not topics:
    st.info("Тем пока нет. Создайте новую выше.")
    st.stop()

topic_labels = {f"{t['name']}  —  ({t['question_count']} вопросов)": t for t in topics}
selected_label = st.selectbox("Выберите тему", list(topic_labels.keys()))
selected_topic = topic_labels[selected_label]

st.subheader("Добавить вопрос в тему")
with st.form("add_question"):
    text = st.text_area("Текст вопроса", height=140)
    ideal = st.text_area("Идеальный ответ (опционально)", height=100)
    diff = st.selectbox("Сложность (опц.)", ["", "easy", "medium", "hard"], index=0)
    submitted_q = st.form_submit_button("Добавить вопрос")
    if submitted_q and text.strip():
        payload = {"text": text.strip(), "ideal_answer": (ideal or None), "difficulty": (diff or None)}
        q = api_post(f"/api/admin/topics/{selected_topic['id']}/questions", payload).json()
        st.success(f"Вопрос добавлен (id={q['id']}).")

st.subheader("Вопросы темы (первые 50)")
try:
    qs = api_get(f"/api/topics/{selected_topic['id']}/questions").json()
    if qs:
        for i, q in enumerate(qs[:50], start=1):
            st.markdown(f"**#{i}.** {q['text']}")
            if q.get("ideal_answer"):
                with st.expander("Эталонный ответ"):
                    st.write(q["ideal_answer"])
    else:
        st.info("В этой теме пока нет вопросов.")
except Exception:
    st.info("Нет прав или ошибка загрузки списка вопросов.")
