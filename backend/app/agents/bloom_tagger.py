from ..llm.router import client

SYSTEM = (
    "Вы — Bloom-Tagger. Отнесите высказывание к уровню таксономии Блума. "
    "Ответьте одним токеном: remember/understand/apply/analyze/evaluate/create."
)


def tag_bloom(text: str) -> str:
    resp = (
        client.chat(
            [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"Высказывание:\n{text}\nУровень? One token (один токен)."},
            ],
            temperature=0.0,
        )
        .strip()
        .lower()
    )
    for k in ["remember", "understand", "apply", "analyze", "evaluate", "create"]:
        if k in resp:
            return k
    return "understand"
