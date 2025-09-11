import json
from ..llm.router import client
from ..llm.errors import RateLimitError, LLMError

SCHEMA_HINT = (
    'Отвечай ТОЛЬКО строгим JSON со следующими ключами: '
    '{"bloom_level": "<remember|understand|apply|analyze|evaluate|create>", '
    '"score": <0..1>, "confidence": <0..1>, "errors": ["..."], "skills": ["algebra","logic",...]}'
)

SYSTEM = (
    "Вы — Judge/Scorer. По вопросу и ответу студента оцените по таксономии Блума. "
    "Учитывайте корректность, глубину рассуждений и обобщение. Возвращайте только структурированный JSON."
)


def _fallback(errors: list[str]) -> dict:
    return {
        "bloom_level": "understand",
        "score": 0.0,
        "confidence": 0.0,
        "errors": errors,
        "skills": [],
    }


def score_answer(question: str, answer: str) -> dict:
    prompt = f"{SCHEMA_HINT}\nВопрос: {question}\nОтвет: {answer}\nВерни только JSON."
    try:
        resp = client.chat(
            [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
            temperature=0.0,
        )
        try:
            return json.loads(resp)
        except Exception:
            return _fallback(["parse_error"])
    except RateLimitError:
        return _fallback(["llm_rate_limited"])
    except LLMError as e:
        return _fallback([f"llm_error:{type(e).__name__}"])
    except Exception:
        return _fallback(["unknown_error"])
