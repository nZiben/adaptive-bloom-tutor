from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select
from .config import settings
from .db import init_db, get_session
from .models import SessionDB, MessageDB, UserDB
from .deps import moderation_guard
from .orchestrator import run_turn
from .reporting import generate_report_png, export_profile_json
from .s3_client import ensure_bucket
from .security import hash_password, verify_password, create_token, get_current_user
from collections import Counter

app = FastAPI(title="AI Tutor Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup():
    init_db()
    ensure_bucket()


# ---------- Auth ----------


class RegisterReq(BaseModel):
    email: EmailStr
    username: str
    password: str


class LoginReq(BaseModel):
    email: EmailStr
    password: str


class TokenResp(BaseModel):
    token: str


@app.post("/api/auth/register", response_model=TokenResp)
def register(req: RegisterReq, s: Session = Depends(get_session)):
    exists = s.exec(select(UserDB).where(UserDB.email == req.email)).first()
    if exists:
        raise HTTPException(400, "Email already registered")
    user = UserDB(email=req.email, username=req.username, password_hash=hash_password(req.password))
    s.add(user)
    s.commit()
    s.refresh(user)
    token = create_token(user.id, user.email)
    return TokenResp(token=token)


@app.post("/api/auth/login", response_model=TokenResp)
def login(req: LoginReq, s: Session = Depends(get_session)):
    user = s.exec(select(UserDB).where(UserDB.email == req.email)).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    token = create_token(user.id, user.email)
    return TokenResp(token=token)


class MeResp(BaseModel):
    id: str
    email: EmailStr
    username: str


@app.get("/api/me", response_model=MeResp)
def me(user: UserDB = Depends(get_current_user)):
    if not user:
        raise HTTPException(401, "Unauthorized")
    return MeResp(id=user.id, email=user.email, username=user.username)


# ---------- Sessions / Chat ----------


class StartSessionReq(BaseModel):
    mode: str  # "exam"|"diagnostic"
    topic: str
    student_id: str | None = None


class StartSessionResp(BaseModel):
    session_id: str
    first_question: str


@app.post("/api/session/start", response_model=StartSessionResp)
def start_session(
    req: StartSessionReq,
    s: Session = Depends(get_session),
    user: UserDB | None = Depends(get_current_user),
):
    se = SessionDB(
        mode=req.mode, topic=req.topic, student_id=req.student_id, user_id=(user.id if user else None)
    )
    s.add(se)
    s.commit()
    s.refresh(se)
    q, _ = run_turn(
        s,
        session_id=se.id,
        topic=req.topic,
        mode=req.mode,
        last_user="Я готов начать.",
        prev_bloom=None,
        prev_diff=None,
        prev_question=None,
    )
    return StartSessionResp(session_id=se.id, first_question=q)


class ChatReq(BaseModel):
    message: str


class ChatResp(BaseModel):
    reply: str
    meta: dict


@app.post("/api/session/{session_id}/message", response_model=ChatResp)
def send_message(
    session_id: str,
    req: ChatReq,
    s: Session = Depends(get_session),
    user: UserDB | None = Depends(get_current_user),
):
    _ = moderation_guard(req.message, session_id=session_id)
    se = s.get(SessionDB, session_id)
    if not se or se.status != "active":
        raise HTTPException(404, "Session not found or inactive")
    if se.user_id and user and se.user_id != user.id:
        raise HTTPException(403, "Forbidden")
    last_q = (
        s.exec(
            select(MessageDB)
            .where(MessageDB.session_id == session_id, MessageDB.role == "assistant")
            .order_by(MessageDB.ts.desc())
        ).first()
    )
    last_bloom = last_q.bloom_level if last_q else None
    prev_diff = "medium"
    reply, meta = run_turn(
        s,
        session_id=session_id,
        topic=se.topic,
        mode=se.mode,
        last_user=req.message,
        prev_bloom=last_bloom,
        prev_diff=prev_diff,
        prev_question=last_q.content if last_q else None,
    )
    return ChatResp(reply=reply, meta=meta)


class ReportResp(BaseModel):
    png_url: str
    json_url: str


@app.get("/api/session/{session_id}/report", response_model=ReportResp)
def get_report(
    session_id: str,
    s: Session = Depends(get_session),
    user: UserDB | None = Depends(get_current_user),
):
    se = s.get(SessionDB, session_id)
    if not se:
        raise HTTPException(404, "Session not found")
    if se.user_id and user and se.user_id != user.id:
        raise HTTPException(403, "Forbidden")
    png = generate_report_png(s, session_id)
    js = export_profile_json(s, session_id)
    return ReportResp(png_url=png, json_url=js)


@app.post("/api/session/{session_id}/complete")
def complete_session(
    session_id: str,
    s: Session = Depends(get_session),
    user: UserDB | None = Depends(get_current_user),
):
    se = s.get(SessionDB, session_id)
    if not se:
        raise HTTPException(404, "Session not found")
    if se.user_id and user and se.user_id != user.id:
        raise HTTPException(403, "Forbidden")
    se.status = "completed"
    s.add(se)
    s.commit()
    return {"ok": True}


# ---------- History / Metrics ----------


class SessionBrief(BaseModel):
    id: str
    topic: str
    mode: str
    status: str
    started_at: str


@app.get("/api/me/sessions", response_model=list[SessionBrief])
def my_sessions(s: Session = Depends(get_session), user: UserDB | None = Depends(get_current_user)):
    if not user:
        raise HTTPException(401, "Unauthorized")
    rows = (
        s.exec(select(SessionDB).where(SessionDB.user_id == user.id).order_by(SessionDB.started_at.desc()))
        .all()
    )
    return [
        SessionBrief(
            id=r.id, topic=r.topic, mode=r.mode, status=r.status, started_at=r.started_at.isoformat()
        )
        for r in rows
    ]


class MessageItem(BaseModel):
    role: str
    content: str
    bloom_level: str | None = None
    solo_level: str | None = None
    score: float | None = None
    ts: str


@app.get("/api/session/{session_id}/messages", response_model=list[MessageItem])
def list_messages(
    session_id: str,
    s: Session = Depends(get_session),
    user: UserDB | None = Depends(get_current_user),
):
    se = s.get(SessionDB, session_id)
    if not se:
        raise HTTPException(404, "Session not found")
    if se.user_id and user and se.user_id != user.id:
        raise HTTPException(403, "Forbidden")
    rows = (
        s.exec(select(MessageDB).where(MessageDB.session_id == session_id).order_by(MessageDB.ts.asc()))
        .all()
    )
    return [
        MessageItem(
            role=m.role,
            content=m.content,
            bloom_level=m.bloom_level,
            solo_level=m.solo_level,
            score=m.score,
            ts=m.ts.isoformat(),
        )
        for m in rows
    ]


class MetricsResp(BaseModel):
    avg_score: float | None
    bloom_counts: dict
    solo_counts: dict
    turns: int


@app.get("/api/session/{session_id}/metrics", response_model=MetricsResp)
def session_metrics(
    session_id: str,
    s: Session = Depends(get_session),
    user: UserDB | None = Depends(get_current_user),
):
    se = s.get(SessionDB, session_id)
    if not se:
        raise HTTPException(404, "Session not found")
    if se.user_id and user and se.user_id != user.id:
        raise HTTPException(403, "Forbidden")
    rows = (
        s.exec(select(MessageDB).where(MessageDB.session_id == session_id).order_by(MessageDB.ts.asc()))
        .all()
    )
    scores = [m.score for m in rows if m.role == "user" and m.score is not None]
    avg = sum(scores) / len(scores) if scores else None
    bloom = Counter([m.bloom_level for m in rows if m.role == "user" and m.bloom_level])
    solo = Counter([m.solo_level for m in rows if m.role == "user" and m.solo_level])
    turns = len([m for m in rows if m.role == "user"])
    return MetricsResp(avg_score=avg, bloom_counts=dict(bloom), solo_counts=dict(solo), turns=turns)


# ---------- Testbench ----------


class TestItem(BaseModel):
    question: str
    ideal_answer: str


class TestbenchReq(BaseModel):
    topic: str
    cases: list[TestItem]


class TestbenchResp(BaseModel):
    per_case: list[dict]
    summary: dict


from .agents.judge import score_answer  # noqa: E402, F401


@app.post("/api/testbench/run", response_model=TestbenchResp)
def run_testbench(req: TestbenchReq):
    per_case = []
    for c in req.cases:
        js = score_answer(c.question, c.ideal_answer)
        per_case.append(
            {
                "question": c.question,
                "score": js.get("score"),
                "bloom": js.get("bloom_level"),
                "confidence": js.get("confidence"),
            }
        )
    scores = [x["score"] for x in per_case if x["score"] is not None]
    summary = {"avg_score": (sum(scores) / len(scores) if scores else None), "n": len(per_case)}
    return TestbenchResp(per_case=per_case, summary=summary)


@app.get("/health")
def health():
    return {"ok": True}
