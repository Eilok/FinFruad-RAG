from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FinFraud-RAG Backend"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""

    siliconflow_api_key: str = ""
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"
    embedding_model: str = "BAAI/bge-m3"

    chroma_persist_dir: str = "./backend/.chroma"
    chroma_collection_name: str = "scam_knowledge_eval"
    eval_collection_prefix: str = "scam_knowledge_eval"

    default_keyword_top_k: int = 3
    default_vector_top_k: int = 3

    ingest_retry_times: int = 2

    request_timeout_seconds: int = 60

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    log_level: str = "INFO"
    log_dir: str = "./backend/logs"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
