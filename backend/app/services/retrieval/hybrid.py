"""
Hybrid retrieval engine combining semantic search, keyword search (BM25), and metadata filtering.
"""

import logging
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple

from app.services.embeddings.provider import EmbeddingProvider, GoogleEmbeddingProvider
from app.services.embeddings.vector_store import VectorStore, VectorSearchResult

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """A single retrieval result with score breakdown."""
    id: str
    content: str
    score: float
    semantic_score: float = 0.0
    keyword_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    content_type: str = "text"
    document_id: Optional[str] = None
    page_number: Optional[int] = None


class BM25:
    """BM25 keyword search implementation."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._corpus: Dict[str, str] = {}  # id -> content
        self._doc_lengths: Dict[str, int] = {}
        self._avg_doc_length: float = 0.0
        self._term_doc_freq: Dict[str, int] = defaultdict(int)  # term -> num docs containing it
        self._doc_term_freq: Dict[str, Dict[str, int]] = {}  # doc_id -> {term: freq}
        self._num_docs: int = 0

    def index_documents(self, documents: Dict[str, str]):
        """Index documents for BM25 search. documents: {id: content}"""
        self._corpus = documents
        self._num_docs = len(documents)

        total_length = 0
        for doc_id, content in documents.items():
            tokens = self._tokenize(content)
            self._doc_lengths[doc_id] = len(tokens)
            total_length += len(tokens)

            term_freq = defaultdict(int)
            for token in tokens:
                term_freq[token] += 1
            self._doc_term_freq[doc_id] = dict(term_freq)

            for term in set(tokens):
                self._term_doc_freq[term] += 1

        self._avg_doc_length = total_length / max(self._num_docs, 1)

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Search documents using BM25 scoring."""
        query_tokens = self._tokenize(query)
        scores = {}

        for doc_id in self._corpus:
            score = 0.0
            doc_length = self._doc_lengths.get(doc_id, 0)
            term_freqs = self._doc_term_freq.get(doc_id, {})

            for term in query_tokens:
                tf = term_freqs.get(term, 0)
                df = self._term_doc_freq.get(term, 0)

                if tf == 0 or df == 0:
                    continue

                # IDF component
                idf = math.log((self._num_docs - df + 0.5) / (df + 0.5) + 1)

                # TF component with length normalization
                tf_norm = (tf * (self.k1 + 1)) / (
                    tf + self.k1 * (1 - self.b + self.b * doc_length / max(self._avg_doc_length, 1))
                )

                score += idf * tf_norm

            if score > 0:
                scores[doc_id] = score

        # Sort by score and return top_k
        sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_results[:top_k]

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple tokenization: lowercase, remove punctuation, split on whitespace."""
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        return [t for t in text.split() if len(t) > 1]


class HybridRetriever:
    """
    Hybrid retrieval engine combining:
    1. Semantic search (vector similarity)
    2. Keyword search (BM25)
    3. Metadata filtering
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ):
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.semantic_weight = semantic_weight
        self.keyword_weight = keyword_weight
        self.bm25 = BM25()
        self._bm25_indexed = False

    def index_for_bm25(self, documents: Dict[str, str]):
        """Index documents for BM25 keyword search."""
        self.bm25.index_documents(documents)
        self._bm25_indexed = True
        logger.info(f"Indexed {len(documents)} documents for BM25")

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        mode: str = "hybrid",  # semantic | keyword | hybrid
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant documents using the specified mode.

        Args:
            query: Natural language query
            top_k: Number of results to return
            filters: Metadata filters (document_id, content_type, page, etc.)
            mode: Retrieval mode (semantic, keyword, hybrid)

        Returns:
            List of RetrievalResult sorted by relevance
        """
        if mode == "semantic":
            return await self._semantic_search(query, top_k, filters)
        elif mode == "keyword":
            return self._keyword_search(query, top_k)
        elif mode == "hybrid":
            return await self._hybrid_search(query, top_k, filters)
        else:
            raise ValueError(f"Unknown retrieval mode: {mode}")

    async def _semantic_search(
        self, query: str, top_k: int, filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """Perform semantic (vector) search."""
        # Use embed_query for query embeddings if available
        if isinstance(self.embedding_provider, GoogleEmbeddingProvider):
            query_embedding = await self.embedding_provider.embed_query(query)
        else:
            query_embedding = await self.embedding_provider.embed_text(query)

        vector_results = await self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            filters=filters,
        )

        results = []
        for vr in vector_results:
            results.append(RetrievalResult(
                id=vr.id,
                content=vr.content,
                score=vr.score,
                semantic_score=vr.score,
                metadata=vr.metadata,
                content_type=vr.metadata.get("content_type", "text"),
                document_id=vr.metadata.get("document_id"),
                page_number=int(vr.metadata["page_number"]) if vr.metadata.get("page_number") else None,
            ))

        return results

    def _keyword_search(self, query: str, top_k: int) -> List[RetrievalResult]:
        """Perform BM25 keyword search."""
        if not self._bm25_indexed:
            return []

        bm25_results = self.bm25.search(query, top_k)

        results = []
        for doc_id, score in bm25_results:
            content = self.bm25._corpus.get(doc_id, "")
            results.append(RetrievalResult(
                id=doc_id,
                content=content,
                score=score,
                keyword_score=score,
            ))

        return results

    async def _hybrid_search(
        self, query: str, top_k: int, filters: Optional[Dict[str, Any]] = None
    ) -> List[RetrievalResult]:
        """
        Combine semantic and keyword search with configurable weights.
        Uses reciprocal rank fusion (RRF) for score combination.
        """
        # Get more results than needed for merging
        fetch_k = top_k * 3

        semantic_results = await self._semantic_search(query, fetch_k, filters)
        keyword_results = self._keyword_search(query, fetch_k)

        # Merge using reciprocal rank fusion
        rrf_scores: Dict[str, float] = {}
        result_map: Dict[str, RetrievalResult] = {}
        k = 60  # RRF constant

        # Score from semantic results
        for rank, result in enumerate(semantic_results):
            rrf_score = self.semantic_weight / (k + rank + 1)
            rrf_scores[result.id] = rrf_scores.get(result.id, 0) + rrf_score
            if result.id not in result_map:
                result_map[result.id] = result
            result_map[result.id].semantic_score = result.score

        # Score from keyword results
        for rank, result in enumerate(keyword_results):
            rrf_score = self.keyword_weight / (k + rank + 1)
            rrf_scores[result.id] = rrf_scores.get(result.id, 0) + rrf_score
            if result.id not in result_map:
                result_map[result.id] = result
            result_map[result.id].keyword_score = result.score

        # Sort by combined RRF score
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        results = []
        for doc_id in sorted_ids[:top_k]:
            result = result_map[doc_id]
            result.score = rrf_scores[doc_id]
            results.append(result)

        return results
