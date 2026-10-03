"""
Core configuration module for the Multimodal RAG Platform.
Manages environment variables, application settings, and feature flags.
"""

import os
from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ─── Application ───────────────────────────────────────────────
    APP_NAME: str = "Multimodal RAG Document Intelligence Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # ─── Server ────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ─── Database ──────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/rag.db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # ─── Redis (optional caching) ──────────────────────────────────
    REDIS_URL: Optional[str] = None

    # ─── AI / LLM ─────────────────────────────────────────────────
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_EMBEDDING_MODEL: str = "models/text-embedding-004"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096

    # ─── Embedding Provider ────────────────────────────────────────
    EMBEDDING_PROVIDER: str = "google"  # google | huggingface | openai
    EMBEDDING_DIMENSION: int = 768
    HUGGINGFACE_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ─── Vector Database ───────────────────────────────────────────
    VECTOR_DB_PROVIDER: str = "chroma"  # chroma | faiss
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    FAISS_INDEX_DIR: str = "./data/faiss"
    CHROMA_COLLECTION_NAME: str = "multimodal_rag"

    # ─── Document Processing ───────────────────────────────────────
    UPLOAD_DIR: str = "./data/uploads"
    PROCESSED_DIR: str = "./data/processed"
    IMAGES_DIR: str = "./data/images"
    MAX_FILE_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: List[str] = [
        ".pdf", ".docx", ".pptx", ".txt",
        ".png", ".jpg", ".jpeg", ".webp"
    ]
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # ─── OCR ───────────────────────────────────────────────────────
    OCR_ENGINE: str = "tesseract"  # tesseract | easyocr
    TESSERACT_CMD: Optional[str] = None

    # ─── Retrieval ─────────────────────────────────────────────────
    RETRIEVAL_TOP_K: int = 10
    RERANK_TOP_K: int = 5
    SEMANTIC_WEIGHT: float = 0.7
    KEYWORD_WEIGHT: float = 0.3
    ENABLE_RERANKING: bool = True
    MAX_QUERY_RETRIES: int = 2

    # ─── Rate Limiting ─────────────────────────────────────────────
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # ─── Security ──────────────────────────────────────────────────
    API_KEY: Optional[str] = None
    ENABLE_API_KEY_AUTH: bool = False
    SECRET_KEY: str = "change-this-in-production-to-a-random-secret"

    # ─── Evaluation ────────────────────────────────────────────────
    ENABLE_RAGAS_EVALUATION: bool = True
    EVALUATION_DATASET_PATH: str = "./data/evaluation"

    @validator("UPLOAD_DIR", "PROCESSED_DIR", "IMAGES_DIR", "CHROMA_PERSIST_DIR",
               "FAISS_INDEX_DIR", "EVALUATION_DATASET_PATH", pre=True)
    def ensure_dirs_exist(cls, v):
        """Ensure data directories exist."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings singleton
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
