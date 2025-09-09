import os
import requests
import streamlit as st

st.set_page_config(page_title="AI Tutor — Метрики", page_icon="📊", layout="wide")
BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")


def api_get(path):
    token = st.session_state.get("token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = requests.get(f"{BACKEND}{path}", headers=headers)
    if not r.ok:
        st.error(f"API error {r.status_code}: {r.text}")
        r.raise_for_status()
    return r


st.title("📊 Метрики сессии")
sid = st.text_input("Session ID", value=st.session_state.get("session_id") or "")
if sid and st.button("Загрузить метрики"):
    mr = api_get(f"/api/session/{sid}/metrics").json()
    st.write(f"Средний score: {mr.get('avg_score')}")
    st.write("Bloom counts:")
    st.json(mr.get("bloom_counts", {}))
    st.write("SOLO counts:")
    st.json(mr.get("solo_counts", {}))
