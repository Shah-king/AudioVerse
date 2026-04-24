"""
Comprehensive test suite for the self-critique pipeline.

Tests are separated into:
  - Unit tests (no LLM calls): evaluator, aggregator, refiner logic
  - Integration tests (no LLM): full pipeline with a mocked LLM critic
  - Scenario tests: predefined user profiles checked against expected conditions
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Allow imports from src/
sys.path.insert(0, str(Path(__file__).parent.parent))

import src.pipeline  # must be imported at module level for @patch to resolve  # noqa: F401
from src.aggregator import aggregate_scores
from src.evaluator import compute_heuristic_score, detect_heuristic_issues
from src.models import EvaluationResult, Playlist, Song, UserInput, load_catalog
from src.pipeline import run_recommendation_pipeline
from src.recommendation_engine import generate_recommendations
from src.refiner import refine_playlist, should_refine

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def catalog() -> list[Song]:
    return load_catalog()


@pytest.fixture
def high_energy_input() -> UserInput:
    return UserInput(
        mood="intense",
        query="high energy workout",
        preferences=["energetic", "aggressive"],
        favorite_genre="pop",
        target_energy=0.92,
        likes_acoustic=False,
        danceability_preference=0.88,
    )


@pytest.fixture
def sad_hopeful_input() -> UserInput:
    return UserInput(
        mood="melancholic",
        query="sad but hopeful songs for late night study",
        preferences=["chill", "focused"],
        favorite_genre="lofi",
        target_energy=0.35,
        likes_acoustic=True,
    )


@pytest.fixture
def chill_input() -> UserInput:
    return UserInput(
        mood="chill",
        query="relaxing background music",
        preferences=["relaxed"],
        favorite_genre="lofi",
        target_energy=0.35,
        likes_acoustic=True,
    )


def _make_playlist(*args: tuple) -> Playlist:
    """Helper: make a Playlist from (title, artist, genre, mood, energy) tuples."""
    songs = [
        Song(
            id=str(i),
            title=t,
            artist=a,
            genre=g,
            mood=m,
            energy=e,
            tempo_bpm=120.0,
            valence=0.5,
            danceability=0.6,
            acousticness=0.3,
        )
        for i, (t, a, g, m, e) in enumerate(args)
    ]
    return Playlist(songs=songs)


# ---------------------------------------------------------------------------
# Evaluator unit tests
# ---------------------------------------------------------------------------

class TestHeuristicEvaluator:
    def test_perfect_diversity(self):
        """5 unique artists → diversity_score = 1.0."""
        playlist = _make_playlist(
            ("Song A", "Artist 1", "pop", "happy", 0.8),
            ("Song B", "Artist 2", "rock", "intense", 0.9),
            ("Song C", "Artist 3", "lofi", "chill", 0.3),
            ("Song D", "Artist 4", "jazz", "relaxed", 0.4),
            ("Song E", "Artist 5", "electronic", "energetic", 0.85),
        )
        user = UserInput(mood="happy", query="test")
        score, metrics = compute_heuristic_score(playlist, user)

        assert metrics["diversity_score"] == pytest.approx(1.0)
        assert metrics["genre_spread"] == pytest.approx(1.0)
        assert score > 7.0, f"Expected score > 7.0 but got {score}"

    def test_zero_diversity_penalty(self):
        """All same artist should yield diversity_score = 0.2 (1 unique / 5)."""
        playlist = _make_playlist(
            ("Song A", "One Artist", "pop", "happy", 0.7),
            ("Song B", "One Artist", "pop", "happy", 0.75),
            ("Song C", "One Artist", "pop", "happy", 0.72),
            ("Song D", "One Artist", "pop", "happy", 0.68),
            ("Song E", "One Artist", "pop", "happy", 0.74),
        )
        user = UserInput(mood="happy", query="test")
        score, metrics = compute_heuristic_score(playlist, user)

        assert metrics["diversity_score"] == pytest.approx(0.2)
        assert metrics["repetition_penalty"] == pytest.approx(0.8)
        assert score < 6.0, f"Expected score < 6.0 but got {score}"

    def test_novelty_with_history(self):
        """Songs in user history should reduce novelty_score."""
        shared_song = Song("hist-1", "Song A", "Artist 1", "pop", "happy", 0.8, 120, 0.7, 0.7, 0.2)
        new_song = Song("new-2", "Song B", "Artist 2", "rock", "intense", 0.9, 140, 0.6, 0.7, 0.1)
        playlist = Playlist(songs=[shared_song, new_song])
        user = UserInput(mood="happy", query="test", history=[shared_song])
        _, metrics = compute_heuristic_score(playlist, user)
        assert metrics["novelty_score"] == pytest.approx(0.5)

    def test_empty_playlist_returns_zero(self):
        user = UserInput(mood="happy", query="test")
        score, metrics = compute_heuristic_score(Playlist(), user)
        assert score == 0.0
        assert metrics == {}

    def test_detect_low_diversity_issue(self):
        metrics = {"diversity_score": 0.3, "genre_spread": 0.8,
                   "novelty_score": 0.9, "repetition_penalty": 0.1}
        issues = detect_heuristic_issues(metrics, threshold=0.6)
        assert any("low_diversity" in i for i in issues)

    def test_no_issues_when_metrics_are_good(self):
        metrics = {"diversity_score": 0.9, "genre_spread": 0.9,
                   "novelty_score": 1.0, "repetition_penalty": 0.0}
        issues = detect_heuristic_issues(metrics, threshold=0.6)
        assert issues == []


# ---------------------------------------------------------------------------
# Aggregator unit tests
# ---------------------------------------------------------------------------

class TestAggregator:
    def test_equal_weights(self):
        result = aggregate_scores(
            heuristic_score=8.0,
            heuristic_metrics={},
            llm_score=6.0,
            llm_feedback=["Good mood alignment"],
            llm_issues=[],
        )
        assert result.reliability_score == pytest.approx(7.0)
        assert result.heuristic_score == 8.0
        assert result.llm_score == 6.0

    def test_issues_merged(self):
        result = aggregate_scores(
            heuristic_score=5.0,
            heuristic_metrics={},
            llm_score=5.0,
            llm_feedback=[],
            llm_issues=["mood_mismatch"],
            heuristic_issues=["low_diversity"],
        )
        assert "mood_mismatch" in result.issues
        assert "low_diversity" in result.issues

    def test_passed_above_threshold(self):
        result = aggregate_scores(8.0, {}, 8.0, [], [])
        assert result.passed(threshold=7.5)

    def test_fails_below_threshold(self):
        result = aggregate_scores(6.0, {}, 6.0, [], [])
        assert not result.passed(threshold=7.5)

    def test_fails_with_issues_even_high_score(self):
        result = aggregate_scores(9.0, {}, 9.0, [], ["mood_mismatch"])
        assert not result.passed(threshold=7.5)


# ---------------------------------------------------------------------------
# Refiner unit tests
# ---------------------------------------------------------------------------

class TestRefiner:
    def test_should_refine_low_score(self):
        ev = EvaluationResult(6.0, 6.0, 6.0)
        assert should_refine(ev, threshold=7.5)

    def test_should_not_refine_high_score_no_issues(self):
        ev = EvaluationResult(8.0, 8.0, 8.0)
        assert not should_refine(ev, threshold=7.5)

    def test_should_refine_if_issues_even_high_score(self):
        ev = EvaluationResult(8.0, 8.0, 8.0, issues=["mood_mismatch"])
        assert should_refine(ev, threshold=7.5)

    def test_refine_returns_different_songs(self, catalog):
        user = UserInput(mood="chill", query="chill music", favorite_genre="lofi",
                         target_energy=0.35, likes_acoustic=True)
        original = generate_recommendations(user, catalog=catalog, k=3)
        evaluation = EvaluationResult(
            5.0, 5.0, 5.0, issues=["low_diversity"]
        )
        refined = refine_playlist(user, original, evaluation, catalog=catalog, k=3)
        original_ids = {s.id for s in original.songs}
        refined_ids = {s.id for s in refined.songs}
        # Refined playlist must introduce at least one new song
        assert len(refined_ids - original_ids) >= 1


# ---------------------------------------------------------------------------
# Recommendation engine tests
# ---------------------------------------------------------------------------

class TestRecommendationEngine:
    def test_returns_k_songs(self, catalog):
        user = UserInput(mood="happy", query="pop hits", favorite_genre="pop",
                         target_energy=0.8)
        playlist = generate_recommendations(user, catalog=catalog, k=5)
        assert len(playlist.songs) == 5

    def test_high_energy_playlist_has_high_avg_energy(self, catalog, high_energy_input):
        playlist = generate_recommendations(high_energy_input, catalog=catalog, k=5)
        avg_energy = sum(s.energy for s in playlist.songs) / len(playlist.songs)
        assert avg_energy >= 0.6, f"Expected avg energy ≥ 0.6 but got {avg_energy:.2f}"

    def test_chill_playlist_has_low_avg_energy(self, catalog, chill_input):
        playlist = generate_recommendations(chill_input, catalog=catalog, k=5)
        avg_energy = sum(s.energy for s in playlist.songs) / len(playlist.songs)
        assert avg_energy <= 0.65, f"Expected avg energy ≤ 0.65 but got {avg_energy:.2f}"

    def test_exclude_ids_respected(self, catalog):
        user = UserInput(mood="chill", query="test", favorite_genre="lofi",
                         target_energy=0.4, likes_acoustic=True)
        first = generate_recommendations(user, catalog=catalog, k=3)
        first_ids = {s.id for s in first.songs}
        second = generate_recommendations(user, catalog=catalog, k=3,
                                          exclude_ids=first_ids)
        overlap = first_ids & {s.id for s in second.songs}
        assert len(overlap) == 0, f"Expected no overlap but got: {overlap}"


# ---------------------------------------------------------------------------
# Scenario (integration) tests — LLM is mocked
# ---------------------------------------------------------------------------

def _mock_llm_good(*args, **kwargs):
    return 8.0, ["Great mood alignment", "Cohesive vibe"], []


def _mock_llm_poor(*args, **kwargs):
    return 4.0, ["Mood mismatch detected"], ["mood_mismatch", "incoherent_vibe"]


class TestScenarios:
    @patch("src.pipeline.evaluate_with_llm", side_effect=_mock_llm_good)
    def test_high_energy_workout_scenario(self, mock_llm, catalog, high_energy_input):
        playlist, evaluation = run_recommendation_pipeline(
            high_energy_input, catalog=catalog, k=5, verbose=False
        )
        assert len(playlist.songs) == 5
        assert evaluation.llm_score == 8.0
        # High energy workout → expect reasonable energy in playlist
        avg_energy = sum(s.energy for s in playlist.songs) / len(playlist.songs)
        assert avg_energy >= 0.55

    @patch("src.pipeline.evaluate_with_llm", side_effect=_mock_llm_good)
    def test_sad_hopeful_scenario(self, mock_llm, catalog, sad_hopeful_input):
        playlist, evaluation = run_recommendation_pipeline(
            sad_hopeful_input, catalog=catalog, k=5, verbose=False
        )
        # Playlist should have at least one melancholic/chill song
        moods = {s.mood.lower() for s in playlist.songs}
        assert len(moods & {"melancholic", "chill", "focused", "relaxed"}) >= 1

    @patch("src.pipeline.evaluate_with_llm", side_effect=_mock_llm_poor)
    def test_poor_evaluation_triggers_refinement(self, mock_llm, catalog, chill_input):
        playlist, evaluation = run_recommendation_pipeline(
            chill_input, catalog=catalog, k=5, verbose=False
        )
        # Should still return a valid playlist despite poor LLM score
        assert len(playlist.songs) >= 1
        assert evaluation.reliability_score < 7.5

    @patch("src.pipeline.evaluate_with_llm", side_effect=_mock_llm_good)
    def test_heuristic_diversity_assertion(self, mock_llm, catalog, chill_input):
        playlist, evaluation = run_recommendation_pipeline(
            chill_input, catalog=catalog, k=5, verbose=False
        )
        diversity = evaluation.heuristic_metrics.get("diversity_score", 0)
        assert diversity >= 0.4, (
            f"Expected diversity ≥ 0.4 but got {diversity:.2f}\n"
            f"Playlist: {[s.artist for s in playlist.songs]}"
        )
