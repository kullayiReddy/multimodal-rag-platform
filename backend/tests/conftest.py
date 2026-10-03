"""
Pytest configuration and test fixtures for Multimodal RAG Platform.
"""

import os
import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Ensure test environment settings
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["VECTOR_DB_PROVIDER"] = "faiss"
os.environ["FAISS_INDEX_DIR"] = "./data/test_faiss"
os.environ["UPLOAD_DIR"] = "./data/test_uploads"
os.environ["PROCESSED_DIR"] = "./data/test_processed"
os.environ["IMAGES_DIR"] = "./data/test_images"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_embedding_provider():
    """Mock embedding provider that returns synthetic 768-dim vectors."""
    provider = MagicMock()
    provider.dimension = 768
    provider.embed_query = AsyncMock(return_value=[0.1] * 768)
    provider.embed_documents = AsyncMock(return_value=[[0.1] * 768, [0.2] * 768])
    return provider


@pytest.fixture
def mock_llm():
    """Mock Gemini LLM returning structured outputs."""
    llm = MagicMock()
    llm.generate = AsyncMock(return_value="According to Table 2, Q3 revenue was $14.2M with a 15% increase.")
    llm.generate_stream = AsyncMock()
    llm.analyze_image = AsyncMock(return_value="A dual-bar chart showing Q1-Q4 revenue comparison across divisions.")
    return llm
