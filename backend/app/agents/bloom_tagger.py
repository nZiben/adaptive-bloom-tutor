from ..llm.router import client
from ..llm.errors import RateLimitError, LLMError

SYSTEM = (
    "Вы — Bloom-Tagger. Отнесите высказывание к уровню таксономии Блума. "
    "Ответьте одним токеном: remember/understand/apply/analyze/evaluate/create."
)

LEVELS = ["remember", "understand", "apply", "analyze", "evaluate", "create"]


def tag_bloom(text: str) -> str:
    try:
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
        for k in LEVELS:
            if k in resp:
                return k
        return "understand"
    except (RateLimitError, LLMError, Exception):
        # На rate limit или ошибках — безопасный дефолт
        return "understand"
