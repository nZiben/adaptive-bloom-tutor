from .mistral_client import MistralClient
from .yandex_client import YandexGPTClient
from ..config import settings

provider = (settings.llm_provider or "mistral").lower()
if provider == "yandex":
    client = YandexGPTClient()
else:
    client = MistralClient()
