import json
from ..llm.router import client

SCHEMA_HINT = (
    'Respond ONLY as strict JSON with keys: '
    '{"bloom_level": "<remember|understand|apply|analyze|evaluate|create>", '
    '"score": <0..1>, "confidence": <0..1>, "errors": ["..."], "skills": ["algebra","logic",...]}'
)

SYSTEM = (
    "You are Judge/Scorer. Given the question and student's answer, assess using Bloom taxonomy. "
    "Consider correctness, reasoning depth, generalization. Return structured JSON only."
)


def score_answer(question: str, answer: str) -> dict:
    prompt = f"{SCHEMA_HINT}\nQuestion:{question}\nAnswer:{answer}\nReturn JSON only."
    resp = client.chat(
        [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
        temperature=0.0,
    )
    try:
        return json.loads(resp)
    except Exception:
        return {
            "bloom_level": "understand",
            "score": 0.0,
            "confidence": 0.0,
            "errors": ["parse_error"],
            "skills": [],
        }
