from typing import Tuple, Dict, List
from sqlmodel import Session, select
from .agents.tutor import generate_question
from .agents.judge import score_answer
from .agents.bloom_tagger import tag_bloom
from .agents.solo_tagger import tag_solo
from .agents.planner import next_bloom, next_difficulty
from .agents.summarizer import recommendations
from .models import MessageDB, SessionDB, TopicDB, QuestionDB
from .assessment import update_ema, irt_update_2pl, aggregate_profile


def _assistant_count(s: Session, session_id: str) -> int:
    rows = s.exec(
        select(MessageDB).where(MessageDB.session_id == session_id, MessageDB.role == "assistant")
    ).all()
    return len(rows)


def _curated_question(s: Session, topic_name: str, index: int) -> str | None:
    topic = s.exec(select(TopicDB).where(TopicDB.name == topic_name)).first()
    if not topic:
        return None
    qs: List[QuestionDB] = (
        s.exec(
            select(QuestionDB)
            .where(QuestionDB.topic_id == topic.id)
            .order_by(QuestionDB.created_at.asc())
        ).all()
    )
    if index < len(qs):
        return qs[index].text
    return None


def run_turn(
    s: Session,
    session_id: str,
    topic: str,
    mode: str,
    last_user: str,
    prev_bloom: str | None,
    prev_diff: str | None,
    prev_question: str | None,
) -> Tuple[str, Dict]:
    """
    Возвращает (assistant_reply, meta).
    В режиме 'exam': после ответа на 10-й вопрос — завершение сессии (без генерации нового вопроса).
    """
    metrics: Dict = {}
    # 1) Сохраняем/оцениваем пользовательский ответ (если был предыдущий вопрос)
    if prev_question:
        js = score_answer(prev_question, last_user)
        metrics = js | {}
        bloom_from_answer = tag_bloom(last_user)
        solo_from_answer = tag_solo(last_user)
        skills = js.get("skills") or ["general"]
        for sk in skills:
            update_ema(s, session_id, sk, js.get("score", 0.0), alpha=0.35)
            irt_update_2pl(s, session_id, sk, js.get("score", 0.0))
        s.add(
            MessageDB(
                session_id=session_id,
                role="user",
                content=last_user,
                bloom_level=bloom_from_answer,
                solo_level=solo_from_answer,
                score=js.get("score"),
                confidence=js.get("confidence"),
                meta=js,
            )
        )
    else:
        s.add(MessageDB(session_id=session_id, role="user", content=last_user))
    s.commit()

    # 2) Проверяем лимит экзамена
    asked = _assistant_count(s, session_id)  # сколько вопросов уже задано
    if mode == "exam":
        # На старте asked==0; после ответа на 10-й вопрос asked==10
        if asked >= 10 and prev_question is not None:
            # Итоговое резюме и авто-завершение
            history_rows = (
                s.exec(
                    select(MessageDB)
                    .where(MessageDB.session_id == session_id)
                    .order_by(MessageDB.ts.asc())
                ).all()
            )
            prof = aggregate_profile(s, session_id)
            scores = [m.score for m in history_rows if m.role == "user" and m.score is not None]
            avg = (sum(scores) / len(scores)) if scores else 0.0
            recs = recommendations(
                topic,
                history=[m.model_dump() for m in history_rows],
                skills={k: v["ema"] for k, v in prof.items()},
            )
            summary = (
                f"Экзамен завершён. Всего вопросов: 10.\n"
                f"Средний score: {avg:.2f}.\n"
                f"Рекомендации:\n{recs}"
            )
            # Сохраним финальное сообщение ассистента (не вопрос)
            s.add(MessageDB(session_id=session_id, role="assistant", content=summary))
            se = s.get(SessionDB, session_id)
            if se:
                se.status = "completed"
                s.add(se)
            s.commit()
            return summary, {
                "completed": True,
                "avg_score": avg,
                "profile": prof,
                "errors": metrics.get("errors", []),
            }

    # 3) Планирование следующего вопроса (или продолжение диагностики)
    current_bloom = prev_bloom or "understand"
    difficulty = prev_diff or "medium"
    score = metrics.get("score", 0.6)
    target_bloom = next_bloom(current_bloom, score, mode)
    next_diff = next_difficulty(difficulty, score)

    # 4) Выбираем источник вопроса:
    #    для exam — сначала пробуем curated (админский банк), иначе fallback на LLM;
    #    для diagnostic — сразу LLM.
    question = None
    if mode == "exam":
        question = _curated_question(s, topic_name=topic, index=asked)  # asked: 0->Q1, 1->Q2, ...
    if not question:
        question = generate_question(
            topic=topic, target_bloom=target_bloom, difficulty=next_diff, last_answer=last_user
        )

    s.add(
        MessageDB(session_id=session_id, role="assistant", content=question, bloom_level=target_bloom)
    )
    s.commit()

    # 5) Рекомендации/профиль (для UI панели)
    history_rows = (
        s.exec(select(MessageDB).where(MessageDB.session_id == session_id).order_by(MessageDB.ts.asc()))
        .all()
    )
    prof = aggregate_profile(s, session_id)
    recs = recommendations(
        topic,
        history=[m.model_dump() for m in history_rows],
        skills={k: v["ema"] for k, v in prof.items()},
    )

    return question, {
        "completed": False,
        "target_bloom": target_bloom,
        "difficulty": next_diff,
        "score": metrics.get("score"),
        "confidence": metrics.get("confidence"),
        "errors": metrics.get("errors", []),
        "profile": prof,
        "recommendations": recs,
    }
