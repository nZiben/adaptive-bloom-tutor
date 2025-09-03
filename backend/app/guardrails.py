import re
from .telemetry import log_event

BANNED = re.compile(r"(bomb|explosive|hate|suicide|nazis|child\s*abuse)", re.I)

def moderate(text: str, *, session_id: str | None = None) -> tuple[bool, str | None]:
    """Returns (is_allowed, reason)."""
    if BANNED.search(text or ""):
        log_event("moderation", {"reason": "banned_term", "text": text}, session_id=session_id)
        return False, "Запрос нарушает правила безопасности."
    if len(text.strip()) > 5000:
        return False, "Слишком длинное сообщение."
    return True, None

