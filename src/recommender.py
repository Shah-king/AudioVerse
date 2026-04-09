import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float


@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py

    Scoring formula (max 6.0 pts):
      +2.0  genre exact match
      +1.0  mood match
      +2.0  energy similarity  →  (1 − |song_energy − target_energy|) × 2
      +0.5  acousticness style match  (bonus)
      +0.5  danceability in range     (bonus, only if danceability_preference set)
    """
    # --- required (tests use these four) ---
    favorite_genre: str
    favorite_mood: str          # single mood or comma-separated for multiple
    target_energy: float
    likes_acoustic: bool

    # --- optional secondary bonuses ---
    danceability_preference: Optional[float] = None   # apply ±0.15 range check
    min_tempo_bpm: Optional[float] = None
    max_tempo_bpm: Optional[float] = None


# ---------------------------------------------------------------------------
# OOP recommender (used by tests)
# ---------------------------------------------------------------------------

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """

    def __init__(self, songs: List[Song]):
        self.songs = songs

    def _score(self, song: Song, user: UserProfile) -> float:
        """Return the total recommendation score for a song against a user profile."""
        score = 0.0

        # Genre match: +2.0
        if song.genre == user.favorite_genre:
            score += 2.0

        # Mood match: +1.0 (supports comma-separated list in favorite_mood)
        # EXPERIMENT: mood check temporarily disabled to observe ranking changes
        # user_moods = [m.strip() for m in user.favorite_mood.split(",")]
        # if song.mood in user_moods:
        #     score += 1.0

        # Energy similarity: (1 − |diff|) × 2.0  →  max 2.0
        score += max(0.0, 1.0 - abs(song.energy - user.target_energy)) * 2.0

        # Acousticness bonus: +0.5 based on likes_acoustic preference
        if user.likes_acoustic and song.acousticness >= 0.6:
            score += 0.5
        elif not user.likes_acoustic and song.acousticness < 0.4:
            score += 0.5

        # Danceability bonus: +0.5 if within ±0.15 of preference
        if user.danceability_preference is not None:
            if abs(song.danceability - user.danceability_preference) <= 0.15:
                score += 0.5

        return score

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top-k songs ranked by score for the given user profile."""
        ranked = sorted(self.songs, key=lambda s: self._score(s, user), reverse=True)
        return ranked[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a human-readable score breakdown explaining why a song was recommended."""
        reasons = []
        score = 0.0

        if song.genre == user.favorite_genre:
            reasons.append(f"genre '{song.genre}' matches (+2.0)")
            score += 2.0

        user_moods = [m.strip() for m in user.favorite_mood.split(",")]
        if song.mood in user_moods:
            reasons.append(f"mood '{song.mood}' matches (+1.0)")
            score += 1.0

        energy_sim = max(0.0, 1.0 - abs(song.energy - user.target_energy)) * 2.0
        reasons.append(f"energy {energy_sim:.2f}/2.0")
        score += energy_sim

        if user.likes_acoustic and song.acousticness >= 0.6:
            reasons.append("acoustic style matches (+0.5)")
            score += 0.5
        elif not user.likes_acoustic and song.acousticness < 0.4:
            reasons.append("electronic style matches (+0.5)")
            score += 0.5

        if user.danceability_preference is not None:
            if abs(song.danceability - user.danceability_preference) <= 0.15:
                reasons.append("danceability in range (+0.5)")
                score += 0.5

        return f"Score {score:.1f}/6.0 — " + "; ".join(reasons)


# ---------------------------------------------------------------------------
# Functional interface (used by src/main.py)
# ---------------------------------------------------------------------------

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file into a list of dicts.
    Required by src/main.py
    """
    songs = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            songs.append({
                "id":           int(row["id"]),
                "title":        row["title"],
                "artist":       row["artist"],
                "genre":        row["genre"],
                "mood":         row["mood"],
                "energy":       float(row["energy"]),
                "tempo_bpm":    float(row["tempo_bpm"]),
                "valence":      float(row["valence"]),
                "danceability": float(row["danceability"]),
                "acousticness": float(row["acousticness"]),
            })
    return songs


def _score_song(song: Dict, user_prefs: Dict) -> Tuple[float, str]:
    """
    Applies the point-based scoring formula to one song.

    Scoring breakdown (max 6.0 pts):
      +2.0  genre exact match
      +1.0  mood match
      +2.0  energy similarity  →  (1 − |song_energy − user_energy|) × 2
      +0.5  danceability in range  (only when 'danceability' key is in user_prefs)
      +0.5  tempo in range         (only when 'min/max_tempo_bpm' keys are present)
    """
    score = 0.0
    reasons = []

    # Genre: +2.0
    if song.get("genre") == user_prefs.get("genre"):
        score += 2.0
        reasons.append(f"genre '{song['genre']}' (+2.0)")

    # Mood: +1.0 (accept str or list)
    # EXPERIMENT: mood check temporarily disabled to observe ranking changes
    # user_mood = user_prefs.get("mood", "")
    # user_moods = user_mood if isinstance(user_mood, list) else [user_mood]
    # if song.get("mood") in user_moods:
    #     score += 1.0
    #     reasons.append(f"mood '{song['mood']}' (+1.0)")

    # Energy similarity: max 2.0
    if "energy" in user_prefs:
        energy_sim = max(0.0, 1.0 - abs(song.get("energy", 0.0) - user_prefs["energy"])) * 2.0
        score += energy_sim
        reasons.append(f"energy similarity (+{energy_sim:.2f})")

    # Danceability bonus: +0.5 if within ±0.15
    if "danceability" in user_prefs:
        if abs(song.get("danceability", 0.0) - user_prefs["danceability"]) <= 0.15:
            score += 0.5
            reasons.append("danceability in range (+0.5)")

    # Tempo bonus: +0.5 if within [min, max]
    if "min_tempo_bpm" in user_prefs and "max_tempo_bpm" in user_prefs:
        if user_prefs["min_tempo_bpm"] <= song.get("tempo_bpm", 0) <= user_prefs["max_tempo_bpm"]:
            score += 0.5
            reasons.append("tempo in range (+0.5)")

    explanation = "; ".join(reasons) if reasons else "no strong match"
    return score, explanation


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """
    Scores all songs against user_prefs, returns top-k as (song, score, explanation).
    Required by src/main.py
    """
    results = []
    for song in songs:
        score, explanation = _score_song(song, user_prefs)
        results.append((song, score, explanation))
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:k]
