import requests
from typing import List, Dict
from ..config import settings

BASE_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1"


class YandexGPTClient:
    def __init__(self, api_key: str | None = None, folder_id: str | None = None):
        self.api_key = api_key or settings.yandex_api_key
        self.folder_id = folder_id or settings.yandex_folder_id
        self.chat_model = settings.yandex_gpt_model
        self.embed_model = settings.yandex_embed_model
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Api-Key {self.api_key}"})

    def _model_uri(self, model: str) -> str:
        return f"gpt://{self.folder_id}/{model}"

    def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.2,
        tools: List[Dict] | None = None,
        response_format: Dict | None = None,
    ) -> str:
        yc_msgs: List[Dict] = []
        for m in messages:
            yc_msgs.append({"role": m.get("role", "user"), "text": m.get("content", "")})
        payload = {
            "modelUri": self._model_uri(self.chat_model),
            "completionOptions": {"stream": False, "temperature": temperature, "maxTokens": "2000"},
            "messages": yc_msgs,
        }
        r = self.session.post(f"{BASE_URL}/completion", json=payload, timeout=60)
        r.raise_for_status()
        js = r.json()
        alts = js.get("result", {}).get("alternatives", [])
        if not alts:
            return ""
        return alts[0]["message"]["text"]

    def embed(self, texts: List[str]) -> List[List[float]]:
        embs: List[List[float]] = []
        for t in texts:
            payload = {"modelUri": self._model_uri(self.embed_model), "text": t}
            r = self.session.post(f"{BASE_URL}/textEmbedding", json=payload, timeout=60)
            r.raise_for_status()
            js = r.json()
            embs.append([float(x) for x in js.get("embedding", [])])
        return embs
