from typing import Optional, Any
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, JSON
from datetime import datetime
import uuid


def uuid_str() -> str:
    return str(uuid.uuid4())


class SessionDB(SQLModel, table=True):
    id: str = Field(default_factory=uuid_str, primary_key=True)
    mode: str = Field(index=True)  # "exam" | "diagnostic"
    topic: str = Field(index=True)
    student_id: Optional[str] = Field(default=None, index=True)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(default="active")  # active/completed


class MessageDB(SQLModel, table=True):
    id: str = Field(default_factory=uuid_str, primary_key=True)
    session_id: str = Field(index=True, foreign_key="sessiondb.id")
    role: str = Field()  # user/assistant/system
    content: str = Field()
    bloom_level: Optional[str] = Field(default=None)
    score: Optional[float] = Field(default=None)
    confidence: Optional[float] = Field(default=None)
    # Use builtin dict typing and explicit Column(JSON)
    meta: Optional[dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)


class SkillScoreDB(SQLModel, table=True):
    id: str = Field(default_factory=uuid_str, primary_key=True)
    session_id: str = Field(index=True)
    skill: str = Field(index=True)
    ema_score: float = Field(default=0.0)       # 0..1
    ema_alpha: float = Field(default=0.3)
    irt_theta: float = Field(default=0.0)       # ability
    last_update: datetime = Field(default_factory=datetime.utcnow)


class EventLogDB(SQLModel, table=True):
    id: str = Field(default_factory=uuid_str, primary_key=True)
    session_id: Optional[str] = Field(default=None, index=True)
    type: str = Field(index=True)  # telemetry, moderation, error, info
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)
