from ..llm.router import client
from ..llm.errors import RateLimitError, LLMError

SYSTEM = (
    "Вы — SOLO-Tagger. Классифицируйте ответ студента по таксономии SOLO. "
    "Верните ОДИН токен: prestructural | unistructural | multistructural | relational | extended-abstract."
)

LEVELS = ["prestructural", "unistructural", "multistructural", "relational", "extended-abstract"]


def tag_solo(text: str) -> str:
    try:
        resp = (
            client.chat(
                [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": f"Ответ:\n{text}\nУровень? ONE TOKEN (один токен)."},
                ],
                temperature=0.0,
            )
            .strip()
            .lower()
        )
        for k in LEVELS:
            if k in resp:
                return k
        return "unistructural"
    except (RateLimitError, LLMError, Exception):
        return "unistructural"
