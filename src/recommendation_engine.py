"""
Recommendation Engine — Module 2.

Retrieves and ranks songs from the catalog using:
  - Feature-vector cosine similarity (embedding search)
  - Metadata filtering (genre, mood, tempo)
  - User history awareness
  - Diversity post-processing reranker
"""
from __future__ import annotations

import math
from typing import Optional

from .models import Playlist, Song, UserInput, load_catalog


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _user_embedding(user: UserInput) -> list[float]:
    """Build a target embedding from user preferences."""
    dance = user.danceability_preference if user.danceability_preference is not None else 0.5
    acoustic = 0.7 if user.likes_acoustic else 0.2
    tempo_mid = 0.5
    if user.min_tempo_bpm and user.max_tempo_bpm:
        tempo_mid = ((user.min_tempo_bpm + user.max_tempo_bpm) / 2) / 200.0
    return [user.target_energy, 0.6, dance, acoustic, tempo_mid]


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _score_song(song: Song, user: UserInput) -> float:
    """
    Hybrid score: content-based rules (0–6.0) + cosine similarity (0–1.0).
    Total max ≈ 7.0 (unnormalized; used only for ranking).
    """
    score = 0.0

    # Genre match
    if song.genre.lower() == user.favorite_genre.lower():
        score += 2.0

    # Mood match (user.mood is the primary mood request)
    user_moods = {m.strip().lower() for m in ([user.mood] + user.preferences)}
    if song.mood.lower() in user_moods:
        score += 1.0

    # Energy similarity
    score += max(0.0, 1.0 - abs(song.energy - user.target_energy)) * 2.0

    # Acousticness style
    if user.likes_acoustic and song.acousticness >= 0.6:
        score += 0.5
    elif not user.likes_acoustic and song.acousticness < 0.4:
        score += 0.5

    # Danceability bonus
    if user.danceability_preference is not None:
        if abs(song.danceability - user.danceability_preference) <= 0.15:
            score += 0.5

    # Tempo bonus
    if user.min_tempo_bpm and user.max_tempo_bpm:
        if user.min_tempo_bpm <= song.tempo_bpm <= user.max_tempo_bpm:
            score += 0.5

    # Embedding cosine similarity (scaled to 0–1)
    cos_sim = _cosine_similarity(song.embedding, _user_embedding(user))
    score += cos_sim

    return score


# ---------------------------------------------------------------------------
# Diversity reranker
# ---------------------------------------------------------------------------

def _apply_diversity_reranker(
    ranked: list[tuple[Song, float]],
    artist_penalty: float = 1.0,
    genre_penalty: float = 0.5,
) -> list[tuple[Song, float]]:
    selected: list[tuple[Song, float]] = []
    seen_artists: set[str] = set()
    seen_genres: set[str] = set()

    for song, score in ranked:
        adjusted = score
        if song.artist in seen_artists:
            adjusted -= artist_penalty
        if song.genre in seen_genres:
            adjusted -= genre_penalty
        selected.append((song, adjusted))
        seen_artists.add(song.artist)
        seen_genres.add(song.genre)

    selected.sort(key=lambda x: x[1], reverse=True)
    return selected


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_recommendations(
    user_input: UserInput,
    catalog: Optional[list[Song]] = None,
    k: int = 5,
    exclude_ids: Optional[set[str]] = None,
) -> Playlist:
    """
    Generate a ranked playlist of k songs for the given user input.

    Args:
        user_input: mood, preferences, history, etc.
        catalog: optional pre-loaded catalog (loads from CSV if None)
        k: number of songs to return
        exclude_ids: song IDs to skip (used by the refiner to force new candidates)
    """
    if catalog is None:
        catalog = load_catalog()

    history_ids = {s.id for s in user_input.history}
    exclude = (exclude_ids or set()) | history_ids

    # Score all candidates
    candidates = [
        (song, _score_song(song, user_input))
        for song in catalog
        if song.id not in exclude
    ]
    candidates.sort(key=lambda x: x[1], reverse=True)

    # Diversity reranker
    candidates = _apply_diversity_reranker(candidates)

    return Playlist(songs=[song for song, _ in candidates[:k]])
