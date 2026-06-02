import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # =========================
    # Vector DB (Qdrant)
    # =========================
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "qdrant-db")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", 6333))

    # =========================
    # LLM APIs
    # =========================
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")

    OLLAMA_BASE_URL: str = os.getenv(
        "OLLAMA_BASE_URL",
        "http://ollama-service:11434"
    )
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3:8b")

    # =========================
    # Embeddings
    # =========================
    EMBEDDING_MODEL: str = "BAAI/bge-large-en-v1.5"

    # =========================
    # Collection
    # =========================
    COLLECTION_NAME: str = "oran_digital_twin"

    class Config:
        env_file = ".env"


settings = Settings()

if not settings.GOOGLE_API_KEY:
    raise ValueError("CRITICAL: GOOGLE_API_KEY is missing")