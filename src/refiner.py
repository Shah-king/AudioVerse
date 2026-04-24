"""
Refinement Module (Agent Loop) — Module 5.

Triggered when reliability_score < threshold OR issues list is non-empty.
Analyses issue tags, adjusts retrieval parameters, and re-calls the
recommendation engine to produce an improved playlist.
"""
from __future__ import annotations

from .models import EvaluationResult, Playlist, Song, UserInput, load_catalog
from .recommendation_engine import generate_recommendations

SCORE_THRESHOLD = 7.5
MAX_ITERATIONS = 2


def _extract_excluded_artists(playlist: Playlist, issues: list[str]) -> set[str]:
    """Return artists that should be dropped due to repetition issues."""
    from collections import Counter
    artist_counts = Counter(s.artist for s in playlist.songs)
    if any("low_diversity" in i or "high_repetition" in i for i in issues):
        return {a for a, c in artist_counts.items() if c > 1}
    return set()


def _boost_mood_weight(user_input: UserInput, issues: list[str]) -> UserInput:
    """
    When mood_mismatch is detected, add explicit mood and related keywords
    to preferences so the recommender ranks mood more heavily.
    """
    if not any("mood_mismatch" in i for i in issues):
        return user_input

    boosted_prefs = list(user_input.preferences)
    if user_input.mood not in boosted_prefs:
        boosted_prefs.insert(0, user_input.mood)
    # Duplicate mood to increase its pull in scoring
    boosted_prefs.insert(0, user_input.mood)

    import dataclasses
    return dataclasses.replace(user_input, preferences=boosted_prefs)


def _adjust_energy(user_input: UserInput, issues: list[str]) -> UserInput:
    """Nudge target_energy toward the query's implied energy level."""
    if not any("energy_mismatch" in i for i in issues):
        return user_input

    import dataclasses
    # Shift energy toward the extreme implied by the mood
    high_energy_moods = {"intense", "energetic", "aggressive", "happy"}
    low_energy_moods = {"chill", "relaxed", "melancholic", "sad", "peaceful"}
    mood = user_input.mood.lower()

    if mood in high_energy_moods:
        new_energy = min(1.0, user_input.target_energy + 0.15)
    elif mood in low_energy_moods:
        new_energy = max(0.0, user_input.target_energy - 0.15)
    else:
        new_energy = user_input.target_energy

    return dataclasses.replace(user_input, target_energy=new_energy)


def refine_playlist(
    user_input: UserInput,
    playlist: Playlist,
    evaluation: EvaluationResult,
    catalog: list[Song] | None = None,
    k: int = 5,
) -> Playlist:
    """
    Produce one refined playlist given the current playlist and its evaluation.

    Strategy:
      1. Exclude artists causing repetition (low_diversity / high_repetition)
      2. Boost mood weight if mood_mismatch detected
      3. Adjust energy target if energy_mismatch detected
      4. Exclude all songs already in the current playlist to force fresh picks
      5. Re-run recommendation engine with the adjusted parameters
    """
    if catalog is None:
        catalog = load_catalog()

    issues = evaluation.issues

    # Excluded song IDs: current playlist + history
    current_ids = {s.id for s in playlist.songs}
    excluded_ids = set(current_ids)

    # Excluded artists
    bad_artists = _extract_excluded_artists(playlist, issues)

    # Filter catalog: remove bad-artist songs and already-seen songs
    refined_catalog = [
        s for s in catalog
        if s.id not in excluded_ids and s.artist not in bad_artists
    ]

    # Adjust user input based on issues
    adjusted_input = _boost_mood_weight(user_input, issues)
    adjusted_input = _adjust_energy(adjusted_input, issues)

    return generate_recommendations(
        adjusted_input,
        catalog=refined_catalog,
        k=k,
    )


def should_refine(evaluation: EvaluationResult, threshold: float = SCORE_THRESHOLD) -> bool:
    return evaluation.reliability_score < threshold or len(evaluation.issues) > 0
