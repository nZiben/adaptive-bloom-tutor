from sqlmodel import Session, select
from .models import SkillScoreDB
from math import exp

def _get_skill(s: Session, session_id: str, skill: str) -> SkillScoreDB:
    row = s.exec(select(SkillScoreDB).where(SkillScoreDB.session_id==session_id, SkillScoreDB.skill==skill)).first()
    if row: return row
    row = SkillScoreDB(session_id=session_id, skill=skill, ema_score=0.5, ema_alpha=0.3, irt_theta=0.0)
    s.add(row); s.commit(); s.refresh(row)
    return row

def update_ema(s: Session, session_id: str, skill: str, score: float, alpha: float = 0.3):
    row = _get_skill(s, session_id, skill)
    row.ema_alpha = alpha
    row.ema_score = alpha*score + (1-alpha)*row.ema_score
    s.add(row); s.commit()

def irt_update_2pl(s: Session, session_id: str, skill: str, score: float, a: float = 1.0, b: float = 0.0, lr: float = 0.1):
    """One-step gradient ascent on theta for 2PL: P=1/(1+exp(-a(theta-b)))."""
    row = _get_skill(s, session_id, skill)
    theta = row.irt_theta
    p = 1/(1+exp(-a*(theta-b)))
    grad = a*(score - p)  # approximate
    row.irt_theta = theta + lr*grad
    s.add(row); s.commit()

def aggregate_profile(s: Session, session_id: str) -> dict:
    rows = s.exec(select(SkillScoreDB).where(SkillScoreDB.session_id==session_id)).all()
    return {r.skill: {"ema": r.ema_score, "theta": r.irt_theta} for r in rows}
