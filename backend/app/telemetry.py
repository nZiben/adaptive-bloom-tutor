from sqlmodel import Session
from .db import engine
from .models import EventLogDB

def log_event(event_type: str, payload: dict, session_id: str | None = None):
    with Session(engine) as s:
        s.add(EventLogDB(type=event_type, payload=payload, session_id=session_id))
        s.commit()
