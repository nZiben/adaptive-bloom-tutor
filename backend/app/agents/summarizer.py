from ..llm.router import client

SYSTEM = "Вы — лаконичный Summarizer/Advisor. Сформируйте короткие, прикладные рекомендации по навыкам с привязкой к уровням Блума."


def recommendations(topic: str, history: list[dict], skills: dict[str, float]) -> str:
    hist_str = "\n".join([f"{m['role']}: {m['content']}" for m in history[-12:]])
    skills_str = "\n".join([f"- {k}: {v:.2f}" for k, v in skills.items()])
    prompt = (
        f"Тема: {topic}\nНедавние ходы:\n{hist_str}\n"
        f"EMA навыков:\n{skills_str}\nДайте 5 кратких, практичных рекомендаций списком."
    )
    return client.chat(
        [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
        temperature=0.3,
    )
