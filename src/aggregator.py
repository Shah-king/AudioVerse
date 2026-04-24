"""
Aggregation Module — Module 4.

Combines heuristic and LLM scores into a single reliability score and
merges their feedback/issues lists.
"""
from __future__ import annotations

from .models import EvaluationResult

HEURISTIC_WEIGHT = 0.5
LLM_WEIGHT = 0.5


def aggregate_scores(
    heuristic_score: float,
    heuristic_metrics: dict,
    llm_score: float,
    llm_feedback: list[str],
    llm_issues: list[str],
    heuristic_issues: list[str] | None = None,
) -> EvaluationResult:
    """
    Merge all evaluation signals into a single EvaluationResult.

    reliability_score = 0.5 * heuristic_score + 0.5 * llm_score
    """
    reliability = round(
        HEURISTIC_WEIGHT * heuristic_score + LLM_WEIGHT * llm_score, 2
    )

    all_issues = list(set((heuristic_issues or []) + llm_issues))
    all_feedback = llm_feedback  # heuristic metrics already captured in metrics dict

    return EvaluationResult(
        heuristic_score=round(heuristic_score, 2),
        llm_score=round(llm_score, 2),
        reliability_score=reliability,
        feedback=all_feedback,
        issues=all_issues,
        heuristic_metrics=heuristic_metrics,
    )
