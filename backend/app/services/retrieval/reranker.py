"""
Reranker for post-retrieval relevance refinement.
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from app.services.retrieval.hybrid import RetrievalResult

logger = logging.getLogger(__name__)


class Reranker:
    """
    Reranker that refines retrieval results based on multiple signals.
    Uses a scoring function considering semantic relevance, keyword overlap,
    content type alignment, and document metadata.
    """

    def __init__(self):
        self._weights = {
            "semantic": 0.4,
            "keyword": 0.2,
            "type_match": 0.2,
            "recency": 0.1,
            "diversity": 0.1,
        }

    async def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        top_k: int = 5,
        query_types: Optional[List[str]] = None,
    ) -> List[RetrievalResult]:
        """
        Rerank retrieval results based on multiple signals.

        Args:
            query: Original query
            results: Initial retrieval results
            top_k: Number of results to keep
            query_types: Expected content types from query classification
        """
        if not results:
            return []

        if len(results) <= top_k:
            return results

        scored_results = []
        seen_content_hashes = set()

        for result in results:
            score = self._compute_rerank_score(
                result=result,
                query=query,
                query_types=query_types,
            )

            # Diversity penalty: reduce score for near-duplicate content
            content_hash = hash(result.content[:200])
            if content_hash in seen_content_hashes:
                score *= 0.5  # Penalize duplicates
            seen_content_hashes.add(content_hash)

            result.score = score
            scored_results.append(result)

        # Sort by reranked score
        scored_results.sort(key=lambda x: x.score, reverse=True)

        reranked = scored_results[:top_k]
        logger.info(
            f"Reranked {len(results)} results to top {len(reranked)} "
            f"(score range: {reranked[-1].score:.3f} - {reranked[0].score:.3f})"
        )
        return reranked

    def _compute_rerank_score(
        self,
        result: RetrievalResult,
        query: str,
        query_types: Optional[List[str]] = None,
    ) -> float:
        """Compute combined reranking score."""
        score = 0.0

        # Semantic relevance (from original retrieval)
        score += self._weights["semantic"] * max(result.semantic_score, 0)

        # Keyword relevance (from BM25 or simple overlap)
        if result.keyword_score > 0:
            # Normalize BM25 score
            normalized_keyword = min(result.keyword_score / 10.0, 1.0)
            score += self._weights["keyword"] * normalized_keyword
        else:
            # Fall back to simple keyword overlap
            overlap = self._keyword_overlap(query, result.content)
            score += self._weights["keyword"] * overlap

        # Content type alignment
        if query_types:
            if result.content_type in query_types:
                score += self._weights["type_match"]
            else:
                score += self._weights["type_match"] * 0.3  # Partial credit

        # Content quality signals
        content_quality = self._content_quality_score(result.content)
        score += self._weights["recency"] * content_quality

        return score

    @staticmethod
    def _keyword_overlap(query: str, content: str) -> float:
        """Simple keyword overlap ratio."""
        query_tokens = set(query.lower().split())
        content_tokens = set(content.lower().split())

        if not query_tokens:
            return 0.0

        overlap = len(query_tokens & content_tokens)
        return overlap / len(query_tokens)

    @staticmethod
    def _content_quality_score(content: str) -> float:
        """Heuristic content quality score."""
        if not content:
            return 0.0

        score = 0.5  # Base score

        # Penalize very short content
        if len(content) < 50:
            score -= 0.2

        # Reward content with structure
        if "\n" in content:
            score += 0.1
        if "|" in content:  # Table-like
            score += 0.1
        if any(c.isdigit() for c in content):
            score += 0.05

        return min(max(score, 0.0), 1.0)
