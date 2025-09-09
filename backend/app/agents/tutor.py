from ..llm.router import client
from ..rag.vectorstore import query

SYSTEM = (
    "You are Tutor-LLM. Generate a single next question or task. "
    "Use Bloom's taxonomy level and difficulty hints. Keep it concise, targeted to the student's last answer and goal topic. "
    "Output only the question text."
)


def generate_question(
    topic: str, target_bloom: str, difficulty: str, last_answer: str, n_docs: int = 4
) -> str:
    hits = query(last_answer or topic, n=n_docs, topic=topic)
    context = "\n\n".join([f"[DOC {i+1}] {h['text']}" for i, h in enumerate(hits)])
    messages = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": (
                f"Topic: {topic}\nTarget Bloom: {target_bloom}\nDifficulty: {difficulty}\n"
                f"Context:\n{context}\nStudent last answer:\n{last_answer}\nGenerate the next question."
            ),
        },
    ]
    return client.chat(messages, temperature=0.4)
