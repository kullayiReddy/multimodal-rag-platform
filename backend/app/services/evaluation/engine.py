"""
RAGAS-compatible evaluation framework for Multimodal RAG.
"""

import logging
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from app.services.retrieval.rag_workflow import RAGWorkflow

logger = logging.getLogger(__name__)


@dataclass
class EvaluationSample:
    """A single evaluation sample."""
    question: str
    ground_truth: str
    category: str = "text"  # text | table | image | cross_modal | multi_doc | unanswerable
    document_ids: Optional[List[str]] = None


@dataclass
class EvaluationMetrics:
    """Computed evaluation metrics."""
    faithfulness: Optional[float] = None
    answer_relevancy: Optional[float] = None
    context_precision: Optional[float] = None
    context_recall: Optional[float] = None
    retrieval_accuracy: Optional[float] = None
    citation_accuracy: Optional[float] = None
    hallucination_rate: Optional[float] = None
    avg_retrieval_latency_ms: float = 0.0
    avg_generation_latency_ms: float = 0.0
    avg_total_latency_ms: float = 0.0
    avg_retrieved_chunks: float = 0.0
    avg_tokens_used: float = 0.0


class EvaluationEngine:
    """
    Evaluation engine computing RAGAS-style metrics.

    Supports:
    - Faithfulness: Does the answer stay true to the context?
    - Answer Relevancy: Is the answer relevant to the question?
    - Context Precision: Is retrieved context relevant?
    - Context Recall: Does context cover the answer?
    - Retrieval Accuracy: Are the right documents retrieved?
    - Citation Accuracy: Are citations correct?
    - Hallucination Rate: How often does the model invent facts?
    """

    def __init__(self, rag_workflow: RAGWorkflow):
        self.workflow = rag_workflow

    async def evaluate(
        self,
        samples: List[EvaluationSample],
        run_name: str = "evaluation",
    ) -> Dict[str, Any]:
        """
        Run evaluation on a set of samples.

        Returns comprehensive evaluation results.
        """
        logger.info(f"Starting evaluation '{run_name}' with {len(samples)} samples")
        start_time = time.time()

        results = []
        total_faithfulness = 0.0
        total_relevancy = 0.0
        total_context_precision = 0.0
        total_context_recall = 0.0
        total_retrieval_latency = 0.0
        total_generation_latency = 0.0
        total_chunks = 0
        total_tokens = 0
        hallucination_count = 0
        correct_citations = 0
        total_citations = 0

        for i, sample in enumerate(samples):
            logger.info(f"Evaluating sample {i + 1}/{len(samples)}: '{sample.question[:60]}...'")

            try:
                # Run RAG workflow
                result = await self.workflow.run(
                    query=sample.question,
                    document_ids=sample.document_ids,
                )

                answer = result.get("answer", "")
                sources = result.get("sources", [])
                retrieval_latency = result.get("retrieval_latency_ms", 0)
                generation_latency = result.get("generation_latency_ms", 0)

                # Compute per-sample metrics
                faithfulness = self._compute_faithfulness(
                    answer=answer,
                    sources=sources,
                    ground_truth=sample.ground_truth,
                )
                relevancy = self._compute_answer_relevancy(
                    question=sample.question,
                    answer=answer,
                )
                context_precision = self._compute_context_precision(
                    sources=sources,
                    ground_truth=sample.ground_truth,
                )
                context_recall = self._compute_context_recall(
                    sources=sources,
                    ground_truth=sample.ground_truth,
                )
                is_hallucination = self._detect_hallucination(
                    answer=answer,
                    sources=sources,
                    ground_truth=sample.ground_truth,
                )

                sample_result = {
                    "question": sample.question,
                    "ground_truth": sample.ground_truth,
                    "answer": answer,
                    "category": sample.category,
                    "faithfulness": faithfulness,
                    "answer_relevancy": relevancy,
                    "context_precision": context_precision,
                    "context_recall": context_recall,
                    "is_hallucination": is_hallucination,
                    "retrieval_latency_ms": retrieval_latency,
                    "generation_latency_ms": generation_latency,
                    "num_sources": len(sources),
                    "tokens_used": result.get("tokens_used", 0),
                }
                results.append(sample_result)

                # Accumulate
                total_faithfulness += faithfulness
                total_relevancy += relevancy
                total_context_precision += context_precision
                total_context_recall += context_recall
                total_retrieval_latency += retrieval_latency
                total_generation_latency += generation_latency
                total_chunks += len(sources)
                total_tokens += result.get("tokens_used", 0)
                if is_hallucination:
                    hallucination_count += 1

            except Exception as e:
                logger.error(f"Evaluation failed for sample {i}: {e}")
                results.append({
                    "question": sample.question,
                    "error": str(e),
                    "category": sample.category,
                })

        n = max(len(samples), 1)
        elapsed = time.time() - start_time

        metrics = {
            "run_name": run_name,
            "dataset_size": len(samples),
            "faithfulness": total_faithfulness / n,
            "answer_relevancy": total_relevancy / n,
            "context_precision": total_context_precision / n,
            "context_recall": total_context_recall / n,
            "hallucination_rate": hallucination_count / n,
            "avg_retrieval_latency_ms": total_retrieval_latency / n,
            "avg_generation_latency_ms": total_generation_latency / n,
            "avg_retrieved_chunks": total_chunks / n,
            "avg_tokens_used": total_tokens / n,
            "total_evaluation_time_seconds": elapsed,
            "per_category": self._aggregate_by_category(results),
            "detailed_results": results,
        }

        logger.info(
            f"Evaluation complete: faithfulness={metrics['faithfulness']:.3f}, "
            f"relevancy={metrics['answer_relevancy']:.3f}, "
            f"hallucination_rate={metrics['hallucination_rate']:.3f}"
        )

        return metrics

    def _compute_faithfulness(
        self, answer: str, sources: List[Dict], ground_truth: str
    ) -> float:
        """
        Compute faithfulness score.
        Measures how well the answer is grounded in the retrieved context.
        Uses keyword overlap between answer and source content.
        """
        if not answer or not sources:
            return 0.0

        answer_tokens = set(answer.lower().split())
        source_tokens = set()
        for source in sources:
            preview = source.get("content_preview", "")
            source_tokens.update(preview.lower().split())

        if not answer_tokens:
            return 0.0

        # How many answer tokens appear in sources
        grounded = len(answer_tokens & source_tokens)
        return min(grounded / len(answer_tokens), 1.0)

    def _compute_answer_relevancy(self, question: str, answer: str) -> float:
        """
        Compute answer relevancy score.
        Measures how relevant the answer is to the question.
        """
        if not answer or not question:
            return 0.0

        q_tokens = set(question.lower().split())
        a_tokens = set(answer.lower().split())

        if not q_tokens:
            return 0.0

        overlap = len(q_tokens & a_tokens)
        return min(overlap / len(q_tokens), 1.0)

    def _compute_context_precision(
        self, sources: List[Dict], ground_truth: str
    ) -> float:
        """
        Compute context precision.
        Measures what fraction of retrieved contexts are relevant.
        """
        if not sources or not ground_truth:
            return 0.0

        gt_tokens = set(ground_truth.lower().split())
        relevant = 0

        for source in sources:
            preview = source.get("content_preview", "")
            source_tokens = set(preview.lower().split())
            overlap = len(gt_tokens & source_tokens)
            if overlap / max(len(gt_tokens), 1) > 0.1:
                relevant += 1

        return relevant / len(sources)

    def _compute_context_recall(
        self, sources: List[Dict], ground_truth: str
    ) -> float:
        """
        Compute context recall.
        Measures how much of the ground truth is covered by retrieved contexts.
        """
        if not sources or not ground_truth:
            return 0.0

        gt_tokens = set(ground_truth.lower().split())
        all_source_tokens = set()
        for source in sources:
            preview = source.get("content_preview", "")
            all_source_tokens.update(preview.lower().split())

        if not gt_tokens:
            return 0.0

        covered = len(gt_tokens & all_source_tokens)
        return min(covered / len(gt_tokens), 1.0)

    def _detect_hallucination(
        self, answer: str, sources: List[Dict], ground_truth: str
    ) -> bool:
        """
        Detect if the answer contains hallucinated content.
        A simple heuristic: if the answer contains claims not found in sources or ground truth.
        """
        if not answer:
            return False

        # Check for explicit "I don't know" responses
        uncertainty_phrases = [
            "cannot answer", "cannot determine", "insufficient",
            "not enough information", "unable to answer",
        ]
        if any(p in answer.lower() for p in uncertainty_phrases):
            return False

        # Check grounding
        answer_tokens = set(answer.lower().split())
        evidence_tokens = set(ground_truth.lower().split())
        for source in sources:
            evidence_tokens.update(source.get("content_preview", "").lower().split())

        grounding_ratio = len(answer_tokens & evidence_tokens) / max(len(answer_tokens), 1)
        return grounding_ratio < 0.3  # Less than 30% grounded = likely hallucination

    def _aggregate_by_category(self, results: List[Dict]) -> Dict[str, Dict]:
        """Aggregate metrics by evaluation category."""
        categories = {}
        for r in results:
            cat = r.get("category", "unknown")
            if cat not in categories:
                categories[cat] = {
                    "count": 0, "faithfulness": 0, "relevancy": 0,
                    "context_precision": 0, "context_recall": 0,
                }
            categories[cat]["count"] += 1
            categories[cat]["faithfulness"] += r.get("faithfulness", 0)
            categories[cat]["relevancy"] += r.get("answer_relevancy", 0)
            categories[cat]["context_precision"] += r.get("context_precision", 0)
            categories[cat]["context_recall"] += r.get("context_recall", 0)

        for cat, data in categories.items():
            n = max(data["count"], 1)
            data["faithfulness"] /= n
            data["relevancy"] /= n
            data["context_precision"] /= n
            data["context_recall"] /= n

        return categories
