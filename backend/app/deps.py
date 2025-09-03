from fastapi import Depends, HTTPException
from .guardrails import moderate

def moderation_guard(text: str, session_id: str | None = None):
    ok, reason = moderate(text, session_id=session_id)
    if not ok:
        raise HTTPException(status_code=400, detail=reason)
    return text

