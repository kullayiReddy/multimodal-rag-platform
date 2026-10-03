"""
Integration tests for FastAPI endpoints.
"""

import pytest
from httpx import AsyncClient
from app.main import create_app


@pytest.mark.asyncio
async def test_health_endpoint():
    """Verify health endpoint returns healthy status and system metadata."""
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


@pytest.mark.asyncio
async def test_documents_list_empty():
    """Verify listing documents returns an empty list or valid paginated response."""
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/documents")
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert "total" in data
