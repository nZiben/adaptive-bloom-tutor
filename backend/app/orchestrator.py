from typing import Tuple, Dict
from sqlmodel import Session, select
from .agents.tutor import generate_question
from .agents.judge import score_answer
from .agents.bloom_tagger import tag_bloom
from .agents.planner import next_bloom, next_difficulty
from .agents.summarizer import recommendations
from .models import MessageDB
from .assessment import update_ema, irt_update_2pl, aggregate_profile

def run_turn(
    s: Session,
    session_id: str,
    topic: str,
    mode: str,
    last_user: str,
    prev_bloom: str | None,
    prev_diff: str | None,
    prev_question: str | None
) -> Tuple[str, Dict]:
    metrics = {}
    if prev_question:
        js = score_answer(prev_question, last_user)
        metrics = js | {}
        bloom_from_answer = tag_bloom(last_user)
        skills = js.get("skills") or ["general"]
        for sk in skills:
            update_ema(s, session_id, sk, js.get("score",0.0), alpha=0.35)
            irt_update_2pl(s, session_id, sk, js.get("score",0.0))
        s.add(MessageDB(session_id=session_id, role="user", content=last_user,
                        bloom_level=bloom_from_answer, score=js.get("score"),
                        confidence=js.get("confidence"), meta=js))
    else:
        s.add(MessageDB(session_id=session_id, role="user", content=last_user))

    s.commit()

    current_bloom = prev_bloom or "understand"
    difficulty = prev_diff or "medium"
    score = metrics.get("score", 0.6)
    target_bloom = next_bloom(current_bloom, score, mode)
    next_diff = next_difficulty(difficulty, score)

    question = generate_question(topic=topic, target_bloom=target_bloom, difficulty=next_diff, last_answer=last_user)

    s.add(MessageDB(session_id=session_id, role="assistant", content=question, bloom_level=target_bloom))
    s.commit()

    # ✅ SQLModel 2.0 style (no legacy .query())
    history_rows = s.exec(select(MessageDB).where(MessageDB.session_id == session_id).order_by(MessageDB.ts.asc())).all()
    prof = aggregate_profile(s, session_id)
    recs = recommendations(
        topic,
        history=[m.model_dump() for m in history_rows],
        skills={k: v["ema"] for k, v in prof.items()}
    )

    return question, {
        "target_bloom": target_bloom,
        "difficulty": next_diff,
        "score": metrics.get("score"),
        "confidence": metrics.get("confidence"),
        "errors": metrics.get("errors", []),
        "profile": prof,
        "recommendations": recs
    }
