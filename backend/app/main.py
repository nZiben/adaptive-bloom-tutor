from collections import Counter
from sqlalchemy import func
from sqlmodel import Session, select
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

from .config import settings
from .db import init_db, get_session
from .models import (
    SessionDB,
    MessageDB,
    UserDB,
    TopicDB,
    QuestionDB,
)
from .deps import moderation_guard
from .orchestrator import run_turn
from .reporting import generate_report_png, export_profile_json
from .s3_client import ensure_bucket
from .security import hash_password, verify_password, create_token, get_current_user
from .agents.judge import score_answer  # <-- добавлено

app = FastAPI(title="AI Tutor Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    ensure_bucket()


# ---------- Auth ----------

class RegisterReq(BaseModel):
    email: EmailStr
    username: str
    password: str
    role: str | None = "student"  # "admin" | "student"


class LoginReq(BaseModel):
    email: EmailStr
    password: str


class TokenResp(BaseModel):
    token: str


def _normalize_role(role: str | None) -> str:
    r = (role or "student").lower().strip()
    return "admin" if r == "admin" else "student"


@app.post("/api/auth/register", response_model=TokenResp)
def register(req: RegisterReq, s: Session = Depends(get_session)) -> TokenResp:
    exists = s.exec(select(UserDB).where(UserDB.email == req.email)).first()
    if exists:
        raise HTTPException(400, "Email already registered")
    role = _normalize_role(req.role)
    user = UserDB(
        email=req.email,
        username=req.username,
        password_hash=hash_password(req.password),
        role=role,
    )
    s.add(user)
    s.commit()
    s.refresh(user)
    token = create_token(user.id, user.email)
    return TokenResp(token=token)


@app.post("/api/auth/login", response_model=TokenResp)
def login(req: LoginReq, s: Session = Depends(get_session)) -> TokenResp:
    user = s.exec(select(UserDB).where(UserDB.email == req.email)).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    token = create_token(user.id, user.email)
    return TokenResp(token=token)


class MeResp(BaseModel):
    id: str
    email: EmailStr
    username: str
    role: str


@app.get("/api/me", response_model=MeResp)
def me(user: UserDB = Depends(get_current_user)) -> MeResp:
    if not user:
        raise HTTPException(401, "Unauthorized")
    return MeResp(id=user.id, email=user.email, username=user.username, role=user.role)


def require_admin(user: UserDB = Depends(get_current_user)) -> UserDB:
    if not user or user.role != "admin":
        raise HTTPException(403, "Admin only")
    return user


# ---------- Admin: Topics / Questions ----------

class TopicCreateReq(BaseModel):
    name: str


class TopicResp(BaseModel):
    id: str
    name: str
    question_count: int


class QuestionCreateReq(BaseModel):
    text: str
    ideal_answer: str | None = None
    bloom_hint: str | None = None
    difficulty: str | None = None  # easy/medium/hard


class QuestionItem(BaseModel):
    id: str
    text: str
    ideal_answer: str | None
    created_at: str


@app.post("/api/admin/topics", response_model=TopicResp)
def admin_create_topic(
    req: TopicCreateReq,
    s: Session = Depends(get_session),
    admin: UserDB = Depends(require_admin),
) -> TopicResp:
    existing = s.exec(select(TopicDB).where(TopicDB.name == req.name)).first()
    if existing:
        raise HTTPException(400, "Topic with this name already exists")
    t = TopicDB(name=req.name, created_by=admin.id)
    s.add(t)
    s.commit()
    s.refresh(t)
    return TopicResp(id=t.id, name=t.name, question_count=0)


@app.post("/api/admin/topics/{topic_id}/questions", response_model=QuestionItem)
def admin_add_question(
    topic_id: str,
    req: QuestionCreateReq,
    s: Session = Depends(get_session),
    _: UserDB = Depends(require_admin),
) -> QuestionItem:
    topic = s.get(TopicDB, topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")
    q = QuestionDB(
        topic_id=topic.id,
        text=req.text,
        ideal_answer=req.ideal_answer,
        bloom_hint=req.bloom_hint,
        difficulty=req.difficulty,
    )
    s.add(q)
    s.commit()
    s.refresh(q)
    return QuestionItem(id=q.id, text=q.text, ideal_answer=q.ideal_answer, created_at=q.created_at.isoformat())


@app.get("/api/topics", response_model=list[TopicResp])
def list_topics(s: Session = Depends(get_session)) -> list[TopicResp]:
    topics = s.exec(select(TopicDB)).all()
    resp: list[TopicResp] = []
    for t in topics:
        cnt = s.exec(select(func.count(QuestionDB.id)).where(QuestionDB.topic_id == t.id)).one()
        count_value = int(cnt[0]) if isinstance(cnt, tuple) else int(cnt)
        resp.append(TopicResp(id=t.id, name=t.name, question_count=count_value))
    return resp


@app.get("/api/topics/{topic_id}/questions", response_model=list[QuestionItem])
def list_topic_questions(
    topic_id: str,
    s: Session = Depends(get_session),
    _: UserDB = Depends(require_admin),
) -> list[QuestionItem]:
    topic = s.get(TopicDB, topic_id)
    if not topic:
        raise HTTPException(404, "Topic not found")
    rows = s.exec(
        select(QuestionDB).where(QuestionDB.topic_id == topic.id).order_by(QuestionDB.created_at.asc())
    ).all()
    return [
        QuestionItem(id=q.id, text=q.text, ideal_answer=q.ideal_answer, created_at=q.created_at.isoformat())
        for q in rows
    ]


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
) -> StartSessionResp:
    se = SessionDB(
        mode=req.mode,
        topic=req.topic,
        student_id=req.student_id,
        user_id=(user.id if user else None),
        max_questions=(10 if req.mode == "exam" else None),
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
) -> ChatResp:
    _ = moderation_guard(req.message, session_id=session_id)
    se = s.get(SessionDB, session_id)
    if not se or se.status != "active":
        raise HTTPException(404, "Session not found or inactive")
    if se.user_id and user and se.user_id != user.id:
        raise HTTPException(403, "Forbidden")

    last_q = s.exec(
        select(MessageDB)
        .where(MessageDB.session_id == session_id, MessageDB.role == "assistant")
        .order_by(MessageDB.ts.desc())
    ).first()
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
) -> ReportResp:
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
) -> dict:
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
def my_sessions(
    s: Session = Depends(get_session),
    user: UserDB | None = Depends(get_current_user),
) -> list[SessionBrief]:
    if not user:
        raise HTTPException(401, "Unauthorized")
    rows = s.exec(
        select(SessionDB)
        .where(SessionDB.user_id == user.id)
        .order_by(SessionDB.started_at.desc())
    ).all()
    return [
        SessionBrief(
            id=r.id,
            topic=r.topic,
            mode=r.mode,
            status=r.status,
            started_at=r.started_at.isoformat(),
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
) -> list[MessageItem]:
    se = s.get(SessionDB, session_id)
    if not se:
        raise HTTPException(404, "Session not found")
    if se.user_id and user and se.user_id != user.id:
        raise HTTPException(403, "Forbidden")
    rows = s.exec(
        select(MessageDB).where(MessageDB.session_id == session_id).order_by(MessageDB.ts.asc())
    ).all()
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
) -> MetricsResp:
    se = s.get(SessionDB, session_id)
    if not se:
        raise HTTPException(404, "Session not found")
    if se.user_id and user and se.user_id != user.id:
        raise HTTPException(403, "Forbidden")
    rows = s.exec(
        select(MessageDB).where(MessageDB.session_id == session_id).order_by(MessageDB.ts.asc())
    ).all()
    scores = [m.score for m in rows if m.role == "user" and m.score is not None]
    avg = sum(scores) / len(scores) if scores else None
    bloom = Counter([m.bloom_level for m in rows if m.role == "user" and m.bloom_level])
    solo = Counter([m.solo_level for m in rows if m.role == "user" and m.solo_level])
    turns = len([m for m in rows if m.role == "user"])
    return MetricsResp(avg_score=avg, bloom_counts=dict(bloom), solo_counts=dict(solo), turns=turns)


# ---------- Testbench ----------

class TestCase(BaseModel):
    question: str
    ideal_answer: str


class TestbenchReq(BaseModel):
    topic: str
    cases: list[TestCase]


@app.post("/api/testbench/run")
def testbench_run(req: TestbenchReq) -> dict:
    """
    Простая проверка: прогоняем эталонные ответы через Judge и возвращаем сырые метрики.
    """
    results = []
    for c in req.cases:
        gold = score_answer(c.question, c.ideal_answer)
        results.append({"question": c.question, "ideal_answer": c.ideal_answer, "eval": gold})
    return {"topic": req.topic, "count": len(results), "results": results}


@app.get("/health")
def health() -> dict:
    return {"ok": True}
