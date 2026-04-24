"""
Core data models for the AI Music Recommender with Self-Critique Loop.
All modules import from here to share a single source of truth.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Song
# ---------------------------------------------------------------------------

@dataclass
class Song:
    id: str
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float
    metadata: dict = field(default_factory=dict)

    @property
    def embedding(self) -> list[float]:
        """5-dim feature vector used for cosine-similarity retrieval."""
        return [
            self.energy,
            self.valence,
            self.danceability,
            self.acousticness,
            min(self.tempo_bpm / 200.0, 1.0),
        ]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "genre": self.genre,
            "mood": self.mood,
            "energy": self.energy,
            "tempo_bpm": self.tempo_bpm,
            "valence": self.valence,
            "danceability": self.danceability,
            "acousticness": self.acousticness,
        }


# ---------------------------------------------------------------------------
# UserInput
# ---------------------------------------------------------------------------

@dataclass
class UserInput:
    mood: str
    query: str
    preferences: list[str] = field(default_factory=list)
    history: list[Song] = field(default_factory=list)
    # Passed through to the recommendation engine
    favorite_genre: str = ""
    target_energy: float = 0.5
    likes_acoustic: bool = False
    danceability_preference: Optional[float] = None
    min_tempo_bpm: Optional[float] = None
    max_tempo_bpm: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "mood": self.mood,
            "query": self.query,
            "preferences": self.preferences,
            "history_ids": [s.id for s in self.history],
            "favorite_genre": self.favorite_genre,
            "target_energy": self.target_energy,
            "likes_acoustic": self.likes_acoustic,
            "danceability_preference": self.danceability_preference,
            "min_tempo_bpm": self.min_tempo_bpm,
            "max_tempo_bpm": self.max_tempo_bpm,
        }


# ---------------------------------------------------------------------------
# Playlist
# ---------------------------------------------------------------------------

@dataclass
class Playlist:
    songs: list[Song] = field(default_factory=list)

    def summary(self) -> str:
        lines = []
        for i, s in enumerate(self.songs, 1):
            lines.append(
                f"{i}. '{s.title}' by {s.artist} "
                f"[{s.genre} | {s.mood} | energy={s.energy:.2f}]"
            )
        return "\n".join(lines)

    def to_dict_list(self) -> list[dict]:
        return [s.to_dict() for s in self.songs]


# ---------------------------------------------------------------------------
# EvaluationResult
# ---------------------------------------------------------------------------

@dataclass
class EvaluationResult:
    heuristic_score: float
    llm_score: float
    reliability_score: float
    feedback: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    heuristic_metrics: dict = field(default_factory=dict)

    def passed(self, threshold: float = 7.5) -> bool:
        return self.reliability_score >= threshold and len(self.issues) == 0


# ---------------------------------------------------------------------------
# LogEntry
# ---------------------------------------------------------------------------

@dataclass
class LogEntry:
    user_input: dict
    initial_playlist: list[dict]
    refined_playlist: list[dict]
    heuristic_score: float
    llm_score: float
    reliability_score: float
    feedback: list[str]
    issues: list[str]
    iterations: int
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return self.__dict__.copy()


# ---------------------------------------------------------------------------
# Catalog loader (shared utility)
# ---------------------------------------------------------------------------

_DEFAULT_CSV = (
    Path(__file__).parent.parent / "data" / "songs.csv"
)


def load_catalog(csv_path: Optional[str] = None) -> list[Song]:
    """Load the song catalog from CSV and return a list of Song objects."""
    path = Path(csv_path) if csv_path else _DEFAULT_CSV
    songs: list[Song] = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            songs.append(
                Song(
                    id=row["id"],
                    title=row["title"],
                    artist=row["artist"],
                    genre=row["genre"],
                    mood=row["mood"],
                    energy=float(row["energy"]),
                    tempo_bpm=float(row["tempo_bpm"]),
                    valence=float(row["valence"]),
                    danceability=float(row["danceability"]),
                    acousticness=float(row["acousticness"]),
                )
            )
    return songs
