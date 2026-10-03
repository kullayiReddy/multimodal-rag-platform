"""
Embedding provider abstraction layer.
Supports Google (Gemini), HuggingFace, and OpenAI embedding backends.
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract interface for embedding generation."""

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Embed a single text string."""
        pass

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts in batch."""
        pass

    @abstractmethod
    async def embed_image(self, image_path: str) -> Optional[List[float]]:
        """Embed an image (returns None if not supported)."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return embedding dimension."""
        pass


class GoogleEmbeddingProvider(EmbeddingProvider):
    """Google Generative AI embedding provider using Gemini."""

    def __init__(self):
        self.settings = get_settings()
        self._dimension = self.settings.EMBEDDING_DIMENSION
        self._model_name = self.settings.GEMINI_EMBEDDING_MODEL
        self._client = None

    def _get_client(self):
        if self._client is None:
            import google.generativeai as genai
            genai.configure(api_key=self.settings.GOOGLE_API_KEY)
            self._client = genai
        return self._client

    async def embed_text(self, text: str) -> List[float]:
        """Embed a single text using Google's embedding model."""
        client = self._get_client()
        try:
            result = client.embed_content(
                model=self._model_name,
                content=text,
                task_type="retrieval_document",
            )
            return result["embedding"]
        except Exception as e:
            logger.error(f"Google embedding error: {e}")
            raise

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts in batch."""
        client = self._get_client()
        try:
            # Google supports batch embedding
            embeddings = []
            batch_size = 100
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                result = client.embed_content(
                    model=self._model_name,
                    content=batch,
                    task_type="retrieval_document",
                )
                embeddings.extend(result["embedding"])
            return embeddings
        except Exception as e:
            logger.error(f"Google batch embedding error: {e}")
            raise

    async def embed_query(self, text: str) -> List[float]:
        """Embed a query (uses retrieval_query task type)."""
        client = self._get_client()
        try:
            result = client.embed_content(
                model=self._model_name,
                content=text,
                task_type="retrieval_query",
            )
            return result["embedding"]
        except Exception as e:
            logger.error(f"Google query embedding error: {e}")
            raise

    async def embed_image(self, image_path: str) -> Optional[List[float]]:
        """Google text-embedding-004 doesn't support images directly."""
        # For image embedding, we use the image description text
        return None

    @property
    def dimension(self) -> int:
        return self._dimension


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    """HuggingFace sentence-transformers embedding provider."""

    def __init__(self):
        self.settings = get_settings()
        self._model = None
        self._model_name = self.settings.HUGGINGFACE_EMBEDDING_MODEL

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
        return self._model

    async def embed_text(self, text: str) -> List[float]:
        model = self._get_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        model = self._get_model()
        embeddings = model.encode(texts, convert_to_numpy=True, batch_size=32)
        return embeddings.tolist()

    async def embed_image(self, image_path: str) -> Optional[List[float]]:
        """Most sentence-transformers don't support image embedding."""
        return None

    @property
    def dimension(self) -> int:
        model = self._get_model()
        return model.get_sentence_embedding_dimension()


def get_embedding_provider() -> EmbeddingProvider:
    """Factory function to get the configured embedding provider."""
    settings = get_settings()
    provider = settings.EMBEDDING_PROVIDER.lower()

    if provider == "google":
        return GoogleEmbeddingProvider()
    elif provider == "huggingface":
        return HuggingFaceEmbeddingProvider()
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")
