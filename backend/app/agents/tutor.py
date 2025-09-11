from ..llm.router import client
from ..llm.errors import RateLimitError, LLMError
from ..rag.vectorstore import query

SYSTEM = (
    "Вы — Tutor-LLM. Сгенерируйте один следующий вопрос или задание. "
    "Используйте уровень таксономии Блума и подсказку по сложности. Будьте кратки, ориентируйтесь на последний ответ студента и целевую тему. "
    "Выведите только текст вопроса."
)


def _fallback_question(topic: str, target_bloom: str, difficulty: str) -> str:
    # Простые шаблоны на случай недоступности провайдера
    stems = {
        "remember": "Дайте определение и приведите краткий пример: ",
        "understand": "Поясните, почему верно следующее утверждение (1–2 предложения): ",
        "apply": "Решите короткую задачу и покажите шаги: ",
        "analyze": "Разберите контрпример/граничный случай и объясните выводы: ",
        "evaluate": "Оцените два подхода и обоснуйте, какой предпочтительнее: ",
        "create": "Сконструируйте свое задание/пример и решите его: ",
    }
    topic_prompts = {
        "linear_algebra": "про линейную алгебру (например, матричное умножение, базис, собственные значения).",
        "probability": "по теории вероятностей (например, формула Байеса, независимость, распределения).",
    }
    stem = stems.get(target_bloom, stems["understand"])
    tail = topic_prompts.get(topic, "по текущей теме.")
    return f"{stem}{tail} Сложность: {difficulty}."

def generate_question(
    topic: str, target_bloom: str, difficulty: str, last_answer: str, n_docs: int = 4
) -> str:
    # Подготовим контекст через RAG (безопасно к падениям)
    try:
        hits = query(last_answer or topic, n=n_docs, topic=topic)
        context = "\n\n".join([f"[DOC {i+1}] {h['text']}" for i, h in enumerate(hits)])
    except Exception:
        hits = []
        context = ""

    messages = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": (
                f"Тема: {topic}\nЦелевой уровень Блума: {target_bloom}\nСложность: {difficulty}\n"
                f"Контекст:\n{context}\nПоследний ответ студента:\n{last_answer}\nСформулируй следующий вопрос."
            ),
        },
    ]
    try:
        return client.chat(messages, temperature=0.4)
    except (RateLimitError, LLMError, Exception):
        # На ошибках — синтетический безопасный вопрос
        return _fallback_question(topic, target_bloom, difficulty)
