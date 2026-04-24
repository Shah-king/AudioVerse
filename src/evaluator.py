"""
Heuristic Evaluator — Module 3A.

Computes objective quality metrics for a playlist without involving an LLM.
All scores are in [0, 10].
"""
from __future__ import annotations

from collections import Counter

from .models import Playlist, UserInput


def compute_heuristic_score(
    playlist: Playlist, user_input: UserInput
) -> tuple[float, dict]:
    """
    Returns (heuristic_score: float, metrics: dict).

    Weighted formula:
        score = (
            0.30 * diversity_score      # unique artists / total
            0.20 * genre_spread         # unique genres / total
            0.20 * novelty_score        # % not in user history
            0.20 * (1 - repetition_penalty)  # penalise artist repeats
            0.10 * popularity_balance   # avoid all-extreme energy
        ) * 10
    """
    songs = playlist.songs
    if not songs:
        return 0.0, {}

    n = len(songs)
    history_ids = {s.id for s in user_input.history}
    artist_counts = Counter(s.artist for s in songs)

    # Diversity: fraction of unique artists
    diversity_score = len(artist_counts) / n

    # Genre spread: fraction of unique genres
    genre_spread = len({s.genre for s in songs}) / n

    # Novelty: fraction of songs the user hasn't heard before
    novel = sum(1 for s in songs if s.id not in history_ids)
    novelty_score = novel / n

    # Repetition penalty: fraction of "excess" songs from the same artist
    repeated = sum(count - 1 for count in artist_counts.values() if count > 1)
    repetition_penalty = repeated / n

    # Popularity balance: energy centred around 0.55 is considered balanced
    avg_energy = sum(s.energy for s in songs) / n
    popularity_balance = max(0.0, 1.0 - abs(avg_energy - 0.55) / 0.45)

    raw = (
        0.30 * diversity_score
        + 0.20 * genre_spread
        + 0.20 * novelty_score
        + 0.20 * (1.0 - repetition_penalty)
        + 0.10 * popularity_balance
    )
    heuristic_score = round(min(raw * 10, 10.0), 2)

    metrics = {
        "diversity_score": round(diversity_score, 3),
        "genre_spread": round(genre_spread, 3),
        "novelty_score": round(novelty_score, 3),
        "repetition_penalty": round(repetition_penalty, 3),
        "popularity_balance": round(popularity_balance, 3),
        "unique_artists": len(artist_counts),
        "unique_genres": len({s.genre for s in songs}),
        "avg_energy": round(avg_energy, 3),
    }

    return heuristic_score, metrics


def detect_heuristic_issues(metrics: dict, threshold: float = 0.6) -> list[str]:
    """
    Convert low metric values into human-readable issue strings that the
    Refinement Module can act on.
    """
    issues: list[str] = []
    if metrics.get("diversity_score", 1.0) < threshold:
        issues.append("low_diversity: too many songs from the same artist")
    if metrics.get("genre_spread", 1.0) < threshold:
        issues.append("low_genre_spread: playlist is genre-monotone")
    if metrics.get("novelty_score", 1.0) < threshold:
        issues.append("low_novelty: most songs are already in user history")
    if metrics.get("repetition_penalty", 0.0) > 0.3:
        issues.append("high_repetition: same artists appear multiple times")
    return issues
