"""
LangGraph-based agentic RAG workflow with query analysis, classification,
multi-modal retrieval, reranking, context validation, and citation generation.
"""

import logging
import time
import json
import uuid
from typing import List, Optional, Dict, Any, TypedDict, Annotated
from dataclasses import dataclass

from langgraph.graph import StateGraph, END

from app.services.llm.gemini import GeminiLLM
from app.services.retrieval.hybrid import HybridRetriever, RetrievalResult
from app.services.retrieval.reranker import Reranker

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


# ─── State Definition ──────────────────────────────────────────────

class RAGState(TypedDict):
    """State flowing through the RAG workflow graph."""
    # Input
    query: str
    document_ids: Optional[List[str]]
    conversation_id: Optional[str]
    top_k: int
    enable_reranking: bool

    # Query analysis
    original_query: str
    rewritten_query: Optional[str]
    query_classification: Optional[Dict[str, Any]]
    query_types: List[str]

    # Retrieval
    retrieval_results: List[Dict[str, Any]]
    text_results: List[Dict[str, Any]]
    table_results: List[Dict[str, Any]]
    image_results: List[Dict[str, Any]]
    retrieval_latency_ms: float

    # Reranking
    reranked_results: List[Dict[str, Any]]

    # Generation
    answer: str
    confidence: Optional[float]
    sources: List[Dict[str, Any]]
    generation_latency_ms: float
    tokens_used: int

    # Control flow
    retry_count: int
    needs_retry: bool
    error: Optional[str]


def _result_to_dict(r: RetrievalResult) -> Dict[str, Any]:
    """Convert RetrievalResult to serializable dict."""
    return {
        "id": r.id,
        "content": r.content,
        "score": r.score,
        "semantic_score": r.semantic_score,
        "keyword_score": r.keyword_score,
        "metadata": r.metadata,
        "content_type": r.content_type,
        "document_id": r.document_id,
        "page_number": r.page_number,
    }


def _dict_to_result(d: Dict[str, Any]) -> RetrievalResult:
    """Convert dict back to RetrievalResult."""
    return RetrievalResult(
        id=d["id"],
        content=d["content"],
        score=d["score"],
        semantic_score=d.get("semantic_score", 0),
        keyword_score=d.get("keyword_score", 0),
        metadata=d.get("metadata", {}),
        content_type=d.get("content_type", "text"),
        document_id=d.get("document_id"),
        page_number=d.get("page_number"),
    )


class RAGWorkflow:
    """
    LangGraph-powered agentic RAG workflow.

    Graph topology:
        START → query_analysis → query_classification → hybrid_retrieval
              → reranking → context_validation → multimodal_generation
              → citation_validation → END

    If retrieval quality is poor, the graph can rewrite the query and retry
    (limited to MAX_RETRIES to prevent infinite loops).
    """

    def __init__(
        self,
        llm: GeminiLLM,
        retriever: HybridRetriever,
        reranker: Reranker,
    ):
        self.llm = llm
        self.retriever = retriever
        self.reranker = reranker
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""
        workflow = StateGraph(RAGState)

        # Add nodes
        workflow.add_node("query_analysis", self._query_analysis)
        workflow.add_node("query_classification", self._query_classification)
        workflow.add_node("hybrid_retrieval", self._hybrid_retrieval)
        workflow.add_node("reranking", self._reranking)
        workflow.add_node("context_validation", self._context_validation)
        workflow.add_node("multimodal_generation", self._multimodal_generation)
        workflow.add_node("citation_validation", self._citation_validation)
        workflow.add_node("query_rewrite", self._query_rewrite)

        # Define edges
        workflow.set_entry_point("query_analysis")
        workflow.add_edge("query_analysis", "query_classification")
        workflow.add_edge("query_classification", "hybrid_retrieval")
        workflow.add_edge("hybrid_retrieval", "reranking")
        workflow.add_edge("reranking", "context_validation")

        # Conditional: retry or generate
        workflow.add_conditional_edges(
            "context_validation",
            self._should_retry,
            {
                "retry": "query_rewrite",
                "generate": "multimodal_generation",
            }
        )

        workflow.add_edge("query_rewrite", "hybrid_retrieval")
        workflow.add_edge("multimodal_generation", "citation_validation")
        workflow.add_edge("citation_validation", END)

        return workflow.compile()

    # ─── Node Functions ──────────────────────────────────────────

    async def _query_analysis(self, state: RAGState) -> Dict[str, Any]:
        """Analyze and normalize the query."""
        query = state["query"].strip()
        logger.info(f"Query analysis: '{query[:80]}...'")

        return {
            "original_query": query,
            "rewritten_query": None,
            "retry_count": 0,
            "needs_retry": False,
            "error": None,
        }

    async def _query_classification(self, state: RAGState) -> Dict[str, Any]:
        """Classify the query to determine retrieval strategy."""
        query = state.get("rewritten_query") or state["query"]

        try:
            classification = await self.llm.classify_query(query)
        except Exception as e:
            logger.warning(f"Classification failed: {e}")
            classification = {
                "types": ["text"],
                "requires_numerical": False,
                "requires_visual": False,
                "complexity": "simple",
            }

        query_types = classification.get("types", ["text"])
        logger.info(f"Query classified: types={query_types}")

        return {
            "query_classification": classification,
            "query_types": query_types,
        }

    async def _hybrid_retrieval(self, state: RAGState) -> Dict[str, Any]:
        """Perform hybrid retrieval across all content types."""
        query = state.get("rewritten_query") or state["query"]
        top_k = state.get("top_k", 10)

        start_time = time.time()

        # Build metadata filters
        filters = {}
        doc_ids = state.get("document_ids")
        if doc_ids and len(doc_ids) == 1:
            filters["document_id"] = str(doc_ids[0])

        # Retrieve across all content types
        all_results = await self.retriever.retrieve(
            query=query,
            top_k=top_k * 2,  # Fetch more for filtering
            filters=filters if filters else None,
            mode="hybrid",
        )

        retrieval_latency = (time.time() - start_time) * 1000

        # Separate by content type
        text_results = []
        table_results = []
        image_results = []

        for r in all_results:
            rd = _result_to_dict(r)
            if r.content_type == "table":
                table_results.append(rd)
            elif r.content_type == "image":
                image_results.append(rd)
            else:
                text_results.append(rd)

        logger.info(
            f"Retrieved: {len(text_results)} text, {len(table_results)} table, "
            f"{len(image_results)} image ({retrieval_latency:.0f}ms)"
        )

        return {
            "retrieval_results": [_result_to_dict(r) for r in all_results],
            "text_results": text_results,
            "table_results": table_results,
            "image_results": image_results,
            "retrieval_latency_ms": retrieval_latency,
        }

    async def _reranking(self, state: RAGState) -> Dict[str, Any]:
        """Rerank retrieval results."""
        if not state.get("enable_reranking", True):
            return {"reranked_results": state.get("retrieval_results", [])}

        results = [_dict_to_result(d) for d in state.get("retrieval_results", [])]
        query_types = state.get("query_types", ["text"])

        reranked = await self.reranker.rerank(
            query=state["query"],
            results=results,
            top_k=state.get("top_k", 5),
            query_types=query_types,
        )

        return {"reranked_results": [_result_to_dict(r) for r in reranked]}

    async def _context_validation(self, state: RAGState) -> Dict[str, Any]:
        """Validate retrieval quality and decide if retry is needed."""
        results = state.get("reranked_results", [])
        retry_count = state.get("retry_count", 0)

        if not results:
            if retry_count < MAX_RETRIES:
                logger.info("No results found, will retry with rewritten query")
                return {"needs_retry": True}
            else:
                return {"needs_retry": False}

        # Check if top results have reasonable scores
        top_score = results[0]["score"] if results else 0
        if top_score < 0.1 and retry_count < MAX_RETRIES:
            logger.info(f"Low retrieval score ({top_score:.3f}), will retry")
            return {"needs_retry": True}

        return {"needs_retry": False}

    def _should_retry(self, state: RAGState) -> str:
        """Decide whether to retry or generate."""
        if state.get("needs_retry", False) and state.get("retry_count", 0) < MAX_RETRIES:
            return "retry"
        return "generate"

    async def _query_rewrite(self, state: RAGState) -> Dict[str, Any]:
        """Rewrite the query for better retrieval."""
        original = state["query"]
        retry_count = state.get("retry_count", 0)

        # Simple query expansion strategies
        if retry_count == 0:
            # Add context words
            rewritten = f"{original} (include relevant details, data, and context)"
        else:
            # Simplify
            rewritten = original.split("?")[0].strip() + "?"

        logger.info(f"Query rewritten (attempt {retry_count + 1}): '{rewritten[:80]}...'")

        return {
            "rewritten_query": rewritten,
            "retry_count": retry_count + 1,
        }

    async def _multimodal_generation(self, state: RAGState) -> Dict[str, Any]:
        """Generate answer using multimodal LLM."""
        query = state["query"]
        results = state.get("reranked_results", [])

        # Prepare context
        text_context = [_dict_to_result(d) for d in results if d.get("content_type") != "image"]
        table_context = [d for d in results if d.get("content_type") == "table"]

        # Get image paths
        image_paths = []
        for d in results:
            if d.get("content_type") == "image":
                img_path = d.get("metadata", {}).get("image_path")
                if img_path:
                    image_paths.append(img_path)

        # Prepare table data for LLM
        table_data = []
        for t in table_context:
            table_data.append({
                "serialized": t.get("content", ""),
                "document_name": t.get("metadata", {}).get("document_name", "Unknown"),
                "page_number": t.get("page_number"),
            })

        # Generate answer
        gen_result = await self.llm.generate_answer(
            query=query,
            text_context=text_context,
            table_context=table_data if table_data else None,
            image_paths=image_paths if image_paths else None,
        )

        return {
            "answer": gen_result["answer"],
            "generation_latency_ms": gen_result["generation_latency_ms"],
            "tokens_used": gen_result.get("tokens_used", 0),
        }

    async def _citation_validation(self, state: RAGState) -> Dict[str, Any]:
        """Build and validate source citations."""
        results = state.get("reranked_results", [])
        sources = []

        for r in results:
            meta = r.get("metadata", {})
            source = {
                "document": meta.get("document_name", "Unknown"),
                "document_id": r.get("document_id", ""),
                "page": r.get("page_number"),
                "content_type": r.get("content_type", "text"),
                "chunk_id": r.get("id", ""),
                "content_preview": r.get("content", "")[:200],
                "score": r.get("score", 0),
            }

            # Add image path if available
            if r.get("content_type") == "image":
                source["image_path"] = meta.get("image_path")

            # Add table data if available
            if r.get("content_type") == "table":
                source["table_data"] = {
                    "headers": meta.get("headers"),
                    "rows": meta.get("rows"),
                }

            sources.append(source)

        # Calculate confidence based on retrieval scores
        if sources:
            avg_score = sum(s["score"] for s in sources) / len(sources)
            confidence = min(avg_score, 1.0)
        else:
            confidence = 0.0

        return {
            "sources": sources,
            "confidence": confidence,
        }

    # ─── Public API ────────────────────────────────────────────

    async def run(
        self,
        query: str,
        document_ids: Optional[List[str]] = None,
        conversation_id: Optional[str] = None,
        top_k: int = 10,
        enable_reranking: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute the full RAG workflow.

        Returns:
            Complete response with answer, sources, latencies, etc.
        """
        initial_state: RAGState = {
            "query": query,
            "document_ids": document_ids,
            "conversation_id": conversation_id,
            "top_k": top_k,
            "enable_reranking": enable_reranking,
            "original_query": query,
            "rewritten_query": None,
            "query_classification": None,
            "query_types": [],
            "retrieval_results": [],
            "text_results": [],
            "table_results": [],
            "image_results": [],
            "retrieval_latency_ms": 0,
            "reranked_results": [],
            "answer": "",
            "confidence": None,
            "sources": [],
            "generation_latency_ms": 0,
            "tokens_used": 0,
            "retry_count": 0,
            "needs_retry": False,
            "error": None,
        }

        total_start = time.time()

        try:
            final_state = await self.graph.ainvoke(initial_state)
        except Exception as e:
            logger.error(f"RAG workflow error: {e}")
            return {
                "answer": f"An error occurred during processing: {str(e)}",
                "confidence": 0.0,
                "sources": [],
                "retrieval_latency_ms": 0,
                "generation_latency_ms": 0,
                "total_latency_ms": (time.time() - total_start) * 1000,
                "error": str(e),
            }

        total_latency = (time.time() - total_start) * 1000

        return {
            "answer": final_state.get("answer", ""),
            "confidence": final_state.get("confidence"),
            "sources": final_state.get("sources", []),
            "retrieval_latency_ms": final_state.get("retrieval_latency_ms", 0),
            "generation_latency_ms": final_state.get("generation_latency_ms", 0),
            "total_latency_ms": total_latency,
            "tokens_used": final_state.get("tokens_used", 0),
            "query_classification": final_state.get("query_classification"),
            "retry_count": final_state.get("retry_count", 0),
        }
