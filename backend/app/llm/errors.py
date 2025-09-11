class LLMError(Exception):
    """Base class for provider-related errors."""
    pass


class RateLimitError(LLMError):
    """Provider returned 429 / rate limited."""
    pass


class ProviderHTTPError(LLMError):
    """Non-429 HTTP error from provider."""

    def __init__(self, status_code: int, body: str | None = None):
        self.status_code = status_code
        self.body = (body or "").strip()
        super().__init__(f"Provider HTTP {status_code}: {self.body[:200]}")
