"""
End-to-End Pipeline Orchestrator — Module 7.

Wires together all modules into a single run_recommendation_pipeline() call.

Flow:
  UserInput
    → generate_recommendations()       [Module 2]
    → compute_heuristic_score()        [Module 3A]
    → evaluate_with_llm()              [Module 3B]
    → aggregate_scores()               [Module 4]
    → (if needed) refine_playlist()    [Module 5]  ← loops up to MAX_ITERATIONS
    → log_event()                      [Module 6]
    → return (final_playlist, evaluation)
"""
from __future__ import annotations

from .aggregator import aggregate_scores
from .evaluator import compute_heuristic_score, detect_heuristic_issues
from .llm_critic import evaluate_with_llm
from .logger import log_event
from .models import EvaluationResult, LogEntry, Playlist, Song, UserInput, load_catalog
from .recommendation_engine import generate_recommendations
from .refiner import MAX_ITERATIONS, SCORE_THRESHOLD, refine_playlist, should_refine

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_recommendation_pipeline(
    user_input: UserInput,
    catalog: list[Song] | None = None,
    k: int = 5,
    threshold: float = SCORE_THRESHOLD,
    max_iterations: int = MAX_ITERATIONS,
    verbose: bool = True,
) -> tuple[Playlist, EvaluationResult]:
    """
    Run the full AI music recommendation pipeline with self-critique loop.

    Returns the final playlist and its EvaluationResult.
    """
    if catalog is None:
        catalog = load_catalog()

    # ---- Step 1: Initial recommendations --------------------------------
    playlist = generate_recommendations(user_input, catalog=catalog, k=k)
    initial_playlist = Playlist(songs=list(playlist.songs))

    if verbose:
        _print_playlist("Initial Playlist", playlist)

    evaluation: EvaluationResult | None = None
    iteration = 0

    # ---- Step 2: Evaluate → Refine loop ---------------------------------
    while iteration < max_iterations:
        heuristic_score, metrics = compute_heuristic_score(playlist, user_input)
        heuristic_issues = detect_heuristic_issues(metrics)

        llm_score, llm_feedback, llm_issues = evaluate_with_llm(user_input, playlist)

        evaluation = aggregate_scores(
            heuristic_score=heuristic_score,
            heuristic_metrics=metrics,
            llm_score=llm_score,
            llm_feedback=llm_feedback,
            llm_issues=llm_issues,
            heuristic_issues=heuristic_issues,
        )

        if verbose:
            _print_evaluation(evaluation, iteration)

        if not should_refine(evaluation, threshold=threshold):
            if verbose:
                print(f"  [OK] Reliability {evaluation.reliability_score}/10 "
                      f">= {threshold} and no issues -- stopping.\n")
            break

        if iteration < max_iterations - 1:
            if verbose:
                print(f"  >> Refining (iteration {iteration + 1}/{max_iterations})...\n")
            playlist = refine_playlist(
                user_input, playlist, evaluation, catalog=catalog, k=k
            )
            if verbose:
                _print_playlist(f"Refined Playlist (iteration {iteration + 1})", playlist)

        iteration += 1

    # Guarantee we always have an evaluation
    if evaluation is None:
        heuristic_score, metrics = compute_heuristic_score(playlist, user_input)
        llm_score, llm_feedback, llm_issues = evaluate_with_llm(user_input, playlist)
        evaluation = aggregate_scores(
            heuristic_score, metrics, llm_score, llm_feedback, llm_issues
        )

    # ---- Step 3: Log everything -----------------------------------------
    entry = LogEntry(
        user_input=user_input.to_dict(),
        initial_playlist=initial_playlist.to_dict_list(),
        refined_playlist=playlist.to_dict_list(),
        heuristic_score=evaluation.heuristic_score,
        llm_score=evaluation.llm_score,
        reliability_score=evaluation.reliability_score,
        feedback=evaluation.feedback,
        issues=evaluation.issues,
        iterations=iteration,
    )
    log_event(entry)

    if verbose:
        _print_final_summary(playlist, evaluation, iteration)

    return playlist, evaluation


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _print_playlist(title: str, playlist: Playlist) -> None:
    print(f"\n{'-' * 56}")
    print(f"  {title}")
    print(f"{'-' * 56}")
    for i, s in enumerate(playlist.songs, 1):
        print(f"  {i}. {s.title:<28} {s.artist:<18} [{s.genre} | {s.mood}]")
    print()


def _print_evaluation(evaluation: EvaluationResult, iteration: int) -> None:
    print(f"{'-' * 56}")
    print(f"  Evaluation (iteration {iteration})")
    print(f"{'-' * 56}")
    m = evaluation.heuristic_metrics
    print(f"  Heuristic  : {evaluation.heuristic_score:>5.2f}/10  "
          f"(diversity={m.get('diversity_score', 0):.2f}, "
          f"genre_spread={m.get('genre_spread', 0):.2f}, "
          f"novelty={m.get('novelty_score', 0):.2f})")
    print(f"  LLM score  : {evaluation.llm_score:>5.2f}/10")
    print(f"  Reliability: {evaluation.reliability_score:>5.2f}/10")
    if evaluation.issues:
        print(f"  Issues     : {', '.join(evaluation.issues)}")
    if evaluation.feedback:
        for fb in evaluation.feedback[:3]:
            print(f"  Feedback   : {fb}")
    print()


def _print_final_summary(
    playlist: Playlist, evaluation: EvaluationResult, iterations: int
) -> None:
    print("=" * 56)
    print("  FINAL PLAYLIST")
    print("=" * 56)
    for i, s in enumerate(playlist.songs, 1):
        print(f"  {i}. {s.title:<28} {s.artist}")
    print()
    print(f"  Reliability Score : {evaluation.reliability_score}/10")
    print(f"  Iterations used   : {iterations}")
    print("=" * 56 + "\n")
