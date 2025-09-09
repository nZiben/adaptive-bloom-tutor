from ..llm.router import client

SYSTEM = "You are a concise Summarizer/Advisor. Produce short, actionable recommendations by skills with Bloom mappings."


def recommendations(topic: str, history: list[dict], skills: dict[str, float]) -> str:
    hist_str = "\n".join([f"{m['role']}: {m['content']}" for m in history[-12:]])
    skills_str = "\n".join([f"- {k}: {v:.2f}" for k, v in skills.items()])
    prompt = (
        f"Topic: {topic}\nRecent turns:\n{hist_str}\n"
        f"Skill EMA:\n{skills_str}\nGive 5 bullet recommendations."
    )
    return client.chat(
        [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
        temperature=0.3,
    )
