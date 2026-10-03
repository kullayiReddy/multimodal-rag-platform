"""
Unit tests for hybrid retrieval, reciprocal rank fusion (RRF), and reranking.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from app.services.retrieval.hybrid import HybridRetriever, RetrievalCandidate


@pytest.mark.asyncio
async def test_reciprocal_rank_fusion():
    """Verify reciprocal rank fusion properly merges dense and sparse results."""
    embedding_mock = MagicMock()
    vector_mock = MagicMock()
    retriever = HybridRetriever(
        embedding_provider=embedding_mock,
        vector_store=vector_mock,
        semantic_weight=0.7,
        keyword_weight=0.3
    )

    dense_candidates = [
        RetrievalCandidate(
            chunk_id="chunk_1",
            content="Q3 Revenue reached $14.2M",
            score=0.92,
            metadata={"page": 3, "content_type": "table"}
        ),
        RetrievalCandidate(
            chunk_id="chunk_2",
            content="Executive summary highlights strong growth",
            score=0.85,
            metadata={"page": 1, "content_type": "text"}
        )
    ]

    sparse_candidates = [
        RetrievalCandidate(
            chunk_id="chunk_1",
            content="Q3 Revenue reached $14.2M",
            score=5.4,
            metadata={"page": 3, "content_type": "table"}
        ),
        RetrievalCandidate(
            chunk_id="chunk_3",
            content="Q3 GAAP Operating Margin table",
            score=4.8,
            metadata={"page": 4, "content_type": "table"}
        )
    ]

    fused = retriever.reciprocal_rank_fusion(
        dense_results=dense_candidates,
        sparse_results=sparse_candidates,
        k=60,
        top_k=3
    )

    assert len(fused) > 0
    # chunk_1 appears in both lists, so it should rank highest!
    assert fused[0].chunk_id == "chunk_1"
    assert fused[0].fused_score > 0
