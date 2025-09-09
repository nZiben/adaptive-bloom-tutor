from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    database_url: str = Field(default="sqlite:///./tutor.db", alias="DATABASE_URL")
    vector_db_dir: str = Field(default="./chroma_store", alias="VECTOR_DB_DIR")
    content_bank_path: str = Field(default="./backend/app/content_bank/seed_content.json", alias="CONTENT_BANK_PATH")

    # LLM routing
    llm_provider: str = Field(default="mistral", alias="LLM_PROVIDER")

    # Mistral
    mistral_api_key: str = Field(default="", alias="MISTRAL_API_KEY")
    mistral_chat_model: str = Field(default="mistral-large-latest", alias="MISTRAL_CHAT_MODEL")
    mistral_embed_model: str = Field(default="mistral-embed", alias="MISTRAL_EMBED_MODEL")

    # YandexGPT
    yandex_api_key: str = Field(default="", alias="YANDEX_API_KEY")
    yandex_folder_id: str = Field(default="", alias="YANDEX_FOLDER_ID")
    yandex_gpt_model: str = Field(default="yandexgpt", alias="YANDEX_GPT_MODEL")
    yandex_embed_model: str = Field(default="text-search-query", alias="YANDEX_EMBED_MODEL")

    # S3/MinIO
    s3_endpoint_url: str = Field(default="http://localhost:9000", alias="S3_ENDPOINT_URL")
    s3_access_key: str = Field(default="minioadmin", alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="minioadmin", alias="S3_SECRET_KEY")
    s3_bucket: str = Field(default="tutor-artifacts", alias="S3_BUCKET")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")

    # Frontend
    frontend_origin: str = Field(default="http://localhost:8501", alias="FRONTEND_ORIGIN")

    # Auth
    auth_secret: str = Field(default="change_me_please", alias="AUTH_SECRET")
    auth_token_ttl_min: int = Field(default=1440, alias="AUTH_TOKEN_TTL_MIN")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()