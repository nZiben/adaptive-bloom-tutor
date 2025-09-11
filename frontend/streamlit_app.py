import os
import requests
import streamlit as st

st.set_page_config(page_title="AI Tutor", page_icon="🎓", layout="wide")

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")

# --------- Auth helpers ---------


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


def load_topics() -> list[dict]:
    try:
        data = api_get("/api/topics").json()
        return data
    except Exception:
        # fallback на статические темы
        return [{"id": "static-la", "name": "linear_algebra", "question_count": 0},
                {"id": "static-prob", "name": "probability", "question_count": 0}]


# --------- Sidebar ---------

st.sidebar.title("AI-Tutor")

if "token" not in st.session_state:
    st.session_state.token = None
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "history" not in st.session_state:
    st.session_state.history = []
if "meta" not in st.session_state:
    st.session_state.meta = {}
if "me" not in st.session_state:
    st.session_state.me = None

with st.sidebar.container():
    if st.session_state.token:
        me = api_get("/api/me").json()
        st.session_state.me = me
        role_badge = "👑 admin" if me.get("role") == "admin" else "🎒 student"
        st.sidebar.success(f"Вошли как: {me['username']} ({role_badge})")
        if st.sidebar.button("Выйти"):
            st.session_state.token = None
            st.session_state.session_id = None
            st.session_state.history = []
            st.session_state.meta = {}
            st.session_state.me = None
            st.rerun()
    else:
        tab_login, tab_reg = st.tabs(["Вход", "Регистрация"])
        with tab_login:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Пароль", type="password", key="login_pass")
            if st.button("Войти"):
                r = api_post("/api/auth/login", {"email": email, "password": password})
                st.session_state.token = r.json()["token"]
                st.success("Готово!")
                st.rerun()
        with tab_reg:
            reg_email = st.text_input("Email для регистрации", key="reg_email")
            username = st.text_input("Имя", key="reg_username")
            role = st.selectbox("Роль", ["student", "admin"], index=0, help="Администратор может создавать темы и вопросы.")
            reg_pass = st.text_input("Пароль (мин. 6 символов)", type="password", key="reg_pass")
            if st.button("Зарегистрироваться"):
                r = api_post(
                    "/api/auth/register",
                    {"email": reg_email, "username": username, "password": reg_pass, "role": role},
                )
                st.session_state.token = r.json()["token"]
                st.success("Аккаунт создан!")
                st.rerun()

# Роль влияет только на админ-страницу; тест можно проходить всем авторизованным
topics = load_topics()
topic_names = [t["name"] for t in topics] or ["linear_algebra", "probability"]

mode = st.sidebar.selectbox("Режим", ["exam", "diagnostic"], help="В 'exam' — ровно 10 вопросов. В 'diagnostic' — без лимита.")
topic = st.sidebar.selectbox("Тема", topic_names)
student_id = st.sidebar.text_input("Student ID (опц.)", "user-1")

if st.session_state.get("token"):
    with st.sidebar.expander("Мои сессии", expanded=False):
        try:
            sessions = api_get("/api/me/sessions").json()
            for s in sessions[:10]:
                st.markdown(
                    f"- {s['started_at'][:16]} • **{s['topic']}** • {s['mode']} • {s['status']}  \n`{s['id']}`"
                )
        except Exception:
            pass

col1, col2 = st.columns([2, 1])

with col1:
    st.header("Чат с тьютором")
    if st.session_state.session_id is None:
        if st.button("Начать сессию"):
            r = api_post(
                "/api/session/start",
                {"mode": mode, "topic": topic, "student_id": student_id},
            )
            data = r.json()
            st.session_state.session_id = data["session_id"]
            st.session_state.history = [{"role": "assistant", "content": data["first_question"]}]
    chat_placeholder = st.container()
    with chat_placeholder:
        for m in st.session_state.history:
            if m["role"] == "assistant":
                st.markdown(f"**Тьютор:** {m['content']}")
            else:
                st.markdown(f"**Вы:** {m['content']}")

    if st.session_state.session_id:
        if "user_input" not in st.session_state:
            st.session_state.user_input = ""
        user_inp = st.text_input("Ваш ответ:", key="user_input")
        if st.button("Отправить") and user_inp.strip():
            st.session_state.history.append({"role": "user", "content": user_inp})
            r = api_post(
                f"/api/session/{st.session_state.session_id}/message", {"message": user_inp}
            )
            data = r.json()
            st.session_state.history.append({"role": "assistant", "content": data["reply"]})
            st.session_state.meta = data["meta"]
            # очистка поля ввода при следующем вопросе
            st.session_state.user_input = ""
            st.rerun()

with col2:
    st.subheader("Статус/метрики")
    meta = st.session_state.get("meta", {})
    st.json(meta if meta else {"info": "Начните сессию"})
    if st.session_state.get("session_id"):
        if st.button("Сгенерировать отчёт"):
            r = api_get(f"/api/session/{st.session_state.session_id}/report")
            if r.ok:
                rep = r.json()
                st.image(rep["png_url"])
                st.markdown(f"[Скачать JSON-профиль]({rep['json_url']})")
        if st.button("Показать метрики сессии"):
            mr = api_get(f"/api/session/{st.session_state.session_id}/metrics").json()
            st.write(f"Средний score: {mr.get('avg_score')}")
            st.write("Bloom counts:")
            st.json(mr.get("bloom_counts", {}))
            st.write("SOLO counts:")
            st.json(mr.get("solo_counts", {}))
        if st.button("Завершить сессию"):
            api_post(f"/api/session/{st.session_state.session_id}/complete", {})
            st.success("Сессия завершена")

st.divider()
st.subheader("Тестбенч")
tb_topic = st.selectbox("Тема тестбенча", topic_names, key="tb_topic")
q1 = st.text_area("Вопрос #1", value="State Bayes' theorem.")
a1 = st.text_area("Идеальный ответ #1", value="Bayes' theorem: P(A|B)=P(B|A)P(A)/P(B).")
if st.button("Запустить тестбенч (1 кейс)"):
    tb = api_post(
        "/api/testbench/run",
        {"topic": tb_topic, "cases": [{"question": q1, "ideal_answer": a1}]},
    ).json()
    st.json(tb)
