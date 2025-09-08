from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Session, select
from .config import settings
from .db import init_db, get_session
from .models import SessionDB, MessageDB
from .deps import moderation_guard
from .orchestrator import run_turn
from .reporting import generate_report_png, export_profile_json
from .s3_client import ensure_bucket

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

class StartSessionReq(BaseModel):
    mode: str  # "exam"|"diagnostic"
    topic: str
    student_id: str | None = None

class StartSessionResp(BaseModel):
    session_id: str
    first_question: str

@app.post("/api/session/start", response_model=StartSessionResp)
def start_session(req: StartSessionReq, s: Session = Depends(get_session)):
    se = SessionDB(mode=req.mode, topic=req.topic, student_id=req.student_id)
    s.add(se); s.commit(); s.refresh(se)
    # Стартовый вопрос без оценки
    q, meta = run_turn(s, session_id=se.id, topic=req.topic, mode=req.mode,
                       last_user="Я готов начать.", prev_bloom=None, prev_diff=None, prev_question=None)
    return StartSessionResp(session_id=se.id, first_question=q)

class ChatReq(BaseModel):
    message: str

class ChatResp(BaseModel):
    reply: str
    meta: dict

@app.post("/api/session/{session_id}/message", response_model=ChatResp)
def send_message(session_id: str, req: ChatReq, s: Session = Depends(get_session)):
    _ = moderation_guard(req.message, session_id=session_id)
    se = s.get(SessionDB, session_id)
    if not se or se.status != "active":
        raise HTTPException(404, "Session not found or inactive")
    # найдём последний вопрос ассистента
    last_q = s.exec(select(MessageDB).where(MessageDB.session_id==session_id, MessageDB.role=="assistant").order_by(MessageDB.ts.desc())).first()
    last_bloom = last_q.bloom_level if last_q else None
    # для простоты считаем что сложность хранится в meta предыдущей реплики ассистента (опустим сохранение в БД)
    prev_diff = "medium"
    reply, meta = run_turn(s, session_id=session_id, topic=se.topic, mode=se.mode,
                           last_user=req.message, prev_bloom=last_bloom, prev_diff=prev_diff,
                           prev_question=last_q.content if last_q else None)
    return ChatResp(reply=reply, meta=meta)

class ReportResp(BaseModel):
    png_url: str
    json_url: str

@app.get("/api/session/{session_id}/report", response_model=ReportResp)
def get_report(session_id: str, s: Session = Depends(get_session)):
    png = generate_report_png(s, session_id)
    js  = export_profile_json(s, session_id)
    return ReportResp(png_url=png, json_url=js)

@app.post("/api/session/{session_id}/complete")
def complete_session(session_id: str, s: Session = Depends(get_session)):
    se = s.get(SessionDB, session_id)
    if not se: raise HTTPException(404, "Session not found")
    se.status = "completed"; s.add(se); s.commit()
    return {"ok": True}

@app.get("/health")
def health():
    return {"ok": True}
