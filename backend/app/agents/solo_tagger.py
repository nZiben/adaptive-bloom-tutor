from ..llm.router import client

SYSTEM = (
    "You are SOLO-Tagger. Classify student's answer by SOLO taxonomy. "
    "Return ONE token: prestructural | unistructural | multistructural | relational | extended-abstract."
)

LEVELS = ["prestructural", "unistructural", "multistructural", "relational", "extended-abstract"]


def tag_solo(text: str) -> str:
    resp = (
        client.chat(
            [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"Answer:\n{text}\nLevel? ONE TOKEN."},
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
