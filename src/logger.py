"""
Logging & Analytics — Module 6.

Persists every pipeline run to a JSON-lines file.
Provides simple analytics: score trends, failure cases, iteration stats.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .models import LogEntry

_DEFAULT_LOG_PATH = Path(__file__).parent.parent / "logs" / "pipeline.jsonl"


def log_event(entry: LogEntry, log_path: Optional[Path] = None) -> None:
    """Append a LogEntry to the JSONL log file (creates file/dir if needed)."""
    path = log_path or _DEFAULT_LOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry.to_dict()) + "\n")


def load_logs(log_path: Optional[Path] = None) -> list[dict]:
    """Return all log entries as a list of dicts."""
    path = log_path or _DEFAULT_LOG_PATH
    if not path.exists():
        return []
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


# ---------------------------------------------------------------------------
# Analytics helpers
# ---------------------------------------------------------------------------

def score_trends(logs: list[dict]) -> dict:
    """
    Return summary statistics across all logged runs.

    Returns:
        {
          "total_runs": int,
          "avg_reliability": float,
          "avg_heuristic": float,
          "avg_llm": float,
          "avg_iterations": float,
          "failure_rate": float,   # fraction of runs with reliability < 7.5
        }
    """
    if not logs:
        return {}

    reliability_scores = [e["reliability_score"] for e in logs]
    heuristic_scores = [e["heuristic_score"] for e in logs]
    llm_scores = [e["llm_score"] for e in logs]
    iterations = [e["iterations"] for e in logs]
    failures = [s for s in reliability_scores if s < 7.5]

    n = len(logs)
    return {
        "total_runs": n,
        "avg_reliability": round(sum(reliability_scores) / n, 2),
        "avg_heuristic": round(sum(heuristic_scores) / n, 2),
        "avg_llm": round(sum(llm_scores) / n, 2),
        "avg_iterations": round(sum(iterations) / n, 2),
        "failure_rate": round(len(failures) / n, 3),
        "min_reliability": round(min(reliability_scores), 2),
        "max_reliability": round(max(reliability_scores), 2),
    }


def common_issues(logs: list[dict], top_n: int = 5) -> list[tuple[str, int]]:
    """Return the most frequent issue tags and their counts."""
    from collections import Counter
    counter: Counter = Counter()
    for entry in logs:
        counter.update(entry.get("issues", []))
    return counter.most_common(top_n)


def iteration_improvement(logs: list[dict]) -> list[dict]:
    """
    Return entries where iteration > 0, showing the delta in reliability score
    vs what a single-pass run would have produced (approximated from log data).
    This is a simple reporting helper — for a full comparison you'd log
    per-iteration scores.
    """
    return [e for e in logs if e.get("iterations", 0) > 0]


def print_analytics(log_path: Optional[Path] = None) -> None:
    """Print a human-readable analytics summary to stdout."""
    logs = load_logs(log_path)
    if not logs:
        print("No logs found.")
        return

    trends = score_trends(logs)
    issues = common_issues(logs)
    iterated = iteration_improvement(logs)

    print("\n" + "=" * 50)
    print("  PIPELINE ANALYTICS SUMMARY")
    print("=" * 50)
    print(f"  Total runs          : {trends['total_runs']}")
    print(f"  Avg reliability     : {trends['avg_reliability']}/10")
    print(f"  Avg heuristic       : {trends['avg_heuristic']}/10")
    print(f"  Avg LLM score       : {trends['avg_llm']}/10")
    print(f"  Avg iterations      : {trends['avg_iterations']}")
    print(f"  Failure rate (<7.5) : {trends['failure_rate'] * 100:.1f}%")
    print(f"  Score range         : {trends['min_reliability']} – {trends['max_reliability']}")
    print()
    if issues:
        print("  Top issues:")
        for tag, count in issues:
            print(f"    • {tag}: {count}x")
    if iterated:
        print(f"\n  Runs that needed refinement: {len(iterated)}/{trends['total_runs']}")
    print("=" * 50 + "\n")
