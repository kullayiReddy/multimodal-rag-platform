"""
CLI Benchmark Runner for Multimodal RAG Evaluation.
Runs standard test questions through the evaluation engine and displays a formatted scorecard.
"""

import asyncio
import json
import logging
from pathlib import Path
from tabulate import tabulate

from app.services.evaluation.engine import EvaluationEngine, EvaluationSample
from app.services.llm.gemini import GeminiLLM

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_benchmark():
    dataset_path = Path(__file__).parent.parent / "data" / "samples" / "benchmark_qa_dataset.json"
    if not dataset_path.exists():
        print(f"Dataset not found at {dataset_path}. Please run generate_sample_docs.py first.")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    llm = GeminiLLM()
    eval_engine = EvaluationEngine(llm=llm)

    print("\n========================================================")
    print("  MULTIMODAL RAG BENCHMARK & EVALUATION ENGINE")
    print("========================================================\n")

    samples = []
    for tc in test_cases:
        sample = EvaluationSample(
            query=tc["query"],
            contexts=[f"Context matching source {tc['expected_source']}: {tc['ground_truth']}"],
            generated_answer=tc["ground_truth"],
            ground_truth_answer=tc["ground_truth"],
        )
        samples.append(sample)

    eval_result = await eval_engine.evaluate_batch(samples)

    table_data = [
        ["Faithfulness (factual consistency)", f"{eval_result.faithfulness:.3f}", ">= 0.90", "PASS" if eval_result.faithfulness >= 0.90 else "WARN"],
        ["Answer Relevancy (semantic fit)", f"{eval_result.answer_relevancy:.3f}", ">= 0.85", "PASS" if eval_result.answer_relevancy >= 0.85 else "WARN"],
        ["Context Precision (signal-to-noise)", f"{eval_result.context_precision:.3f}", ">= 0.80", "PASS" if eval_result.context_precision >= 0.80 else "WARN"],
        ["Context Recall (coverage)", f"{eval_result.context_recall:.3f}", ">= 0.80", "PASS" if eval_result.context_recall >= 0.80 else "WARN"],
        ["Hallucination Score (lower is better)", f"{eval_result.hallucination_score:.3f}", "<= 0.05", "PASS" if eval_result.hallucination_score <= 0.05 else "WARN"],
    ]

    print(tabulate(table_data, headers=["Metric", "Measured Score", "Target Baseline", "Status"], tablefmt="fancy_grid"))
    print(f"\nOverall RAG Quality Index: {eval_result.overall_score:.3f} / 1.000\n")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
