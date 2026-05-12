from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FinFraud-RAG Backend"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""

    embedding_model: str = ""
    chroma_persist_dir: str = "./backend/.chroma"

    default_keyword_top_k: int = 5
    default_vector_top_k: int = 5

    log_level: str = "INFO"
    log_dir: str = "./backend/logs"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
