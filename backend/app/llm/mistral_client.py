import requests
from typing import List, Dict
from ..config import settings

API_URL = "https://api.mistral.ai/v1"


class MistralClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.mistral_api_key
        self.chat_model = settings.mistral_chat_model
        self.embed_model = settings.mistral_embed_model
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})

    def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.2,
        tools: List[Dict] | None = None,
        response_format: Dict | None = None,
    ) -> str:
        payload: Dict = {"model": self.chat_model, "messages": messages, "temperature": temperature}
        if tools:
            payload["tools"] = tools
        if response_format:
            payload["response_format"] = response_format
        r = self.session.post(f"{API_URL}/chat/completions", json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    def embed(self, texts: List[str]) -> List[List[float]]:
        r = self.session.post(
            f"{API_URL}/embeddings",
            json={"model": self.embed_model, "input": texts},
            timeout=60,
        )
        r.raise_for_status()
        return [d["embedding"] for d in r.json()["data"]]
