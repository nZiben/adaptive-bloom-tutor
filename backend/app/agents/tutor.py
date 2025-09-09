from ..llm.router import client
from ..rag.vectorstore import query

SYSTEM = (
    "Вы — Tutor-LLM. Сгенерируйте один следующий вопрос или задание. "
    "Используйте уровень таксономии Блума и подсказку по сложности. Будьте кратки, ориентируйтесь на последний ответ студента и целевую тему. "
    "Выведите только текст вопроса."
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
                f"Тема: {topic}\nЦелевой уровень Блума: {target_bloom}\nСложность: {difficulty}\n"
                f"Контекст:\н{context}\nПоследний ответ студента:\n{last_answer}\nСформулируй следующий вопрос."
            ),
        },
    ]
    return client.chat(messages, temperature=0.4)
