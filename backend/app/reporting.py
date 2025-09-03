import io, json
import matplotlib.pyplot as plt
from sqlmodel import Session, select
from .models import MessageDB
from .assessment import aggregate_profile
from .s3_client import put_bytes, put_json

def generate_report_png(s: Session, session_id: str) -> str:
    prof = aggregate_profile(s, session_id)
    skills = list(prof.keys()) or ["general"]
    values = [prof[k]["ema"] for k in skills] or [0.5]

    fig, ax = plt.subplots(figsize=(6,4))
    ax.bar(skills, values)
    ax.set_ylim(0,1); ax.set_ylabel("EMA score"); ax.set_title("Skill profile")
    buf = io.BytesIO()
    plt.tight_layout(); fig.savefig(buf, format="png"); plt.close(fig)
    key = f"reports/{session_id}/skill_profile.png"
    return put_bytes(key, buf.getvalue(), "image/png")

def export_profile_json(s: Session, session_id: str) -> str:
    prof = aggregate_profile(s, session_id)
    # Minimal LMS-ready JSON
    data = {
        "session_id": session_id,
        "profile": [{"skill": k, "ema": v["ema"], "theta": v["theta"]} for k,v in prof.items()]
    }
    key = f"reports/{session_id}/profile.json"
    return put_json(key, data)
