import io
import matplotlib.pyplot as plt
from collections import Counter
from sqlmodel import Session, select
from .models import MessageDB
from .assessment import aggregate_profile
from .s3_client import put_bytes, put_json


def _bloom_solo_counts(msgs: list[MessageDB]):
    bloom = Counter([m.bloom_level for m in msgs if m.role == "user" and m.bloom_level])
    solo = Counter([m.solo_level for m in msgs if m.role == "user" and m.solo_level])
    return bloom, solo


def generate_report_png(s: Session, session_id: str) -> str:
    prof = aggregate_profile(s, session_id)
    skills = list(prof.keys()) or ["general"]
    values = [prof[k]["ema"] for k in skills] or [0.5]

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(skills, values)
    ax.set_ylim(0, 1)
    ax.set_ylabel("EMA score")
    ax.set_title("Skill profile")
    buf = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    key = f"reports/{session_id}/skill_profile.png"
    return put_bytes(key, buf.getvalue(), "image/png")


def export_profile_json(s: Session, session_id: str) -> str:
    prof = aggregate_profile(s, session_id)
    msgs = (
        s.exec(select(MessageDB).where(MessageDB.session_id == session_id).order_by(MessageDB.ts.asc()))
        .all()
    )
    bloom_c, solo_c = _bloom_solo_counts(msgs)
    scores = [m.score for m in msgs if m.role == "user" and m.score is not None]
    avg_score = (sum(scores) / len(scores)) if scores else None
    data = {
        "session_id": session_id,
        "profile": [{"skill": k, "ema": v["ema"], "theta": v["theta"]} for k, v in prof.items()],
        "metrics": {
            "avg_score": avg_score,
            "bloom_counts": dict(bloom_c),
            "solo_counts": dict(solo_c),
            "turns": len([m for m in msgs if m.role == "user"]),
        },
    }
    key = f"reports/{session_id}/profile.json"
    return put_json(key, data)
