"""
Human Feedback Module — Module 8 (Optional).

Collects user ratings and comments on a playlist.
Stores feedback alongside the pipeline log so it can later be used
to calibrate scoring weights.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import Playlist

_DEFAULT_FEEDBACK_PATH = (
    Path(__file__).parent.parent / "logs" / "human_feedback.jsonl"
)


def collect_user_feedback(
    playlist: Playlist,
    session_id: Optional[str] = None,
    feedback_path: Optional[Path] = None,
) -> dict:
    """
    Interactively prompt the user for a rating and optional comment.
    Saves the response to disk and returns the feedback dict.

    Args:
        playlist: the playlist the user is rating
        session_id: optional run identifier for joining with pipeline logs
        feedback_path: override the default feedback log location

    Returns:
        {
          "session_id": str | None,
          "rating": int (1–5),
          "comments": str,
          "songs": [song titles],
          "timestamp": ISO-8601 str,
        }
    """
    print("\n" + "=" * 50)
    print("  HUMAN FEEDBACK")
    print("=" * 50)
    print("  Please rate the playlist below:\n")
    for i, s in enumerate(playlist.songs, 1):
        print(f"  {i}. {s.title} — {s.artist}")
    print()

    rating = _prompt_rating()
    comments = input("  Any comments? (press Enter to skip): ").strip()

    feedback = {
        "session_id": session_id,
        "rating": rating,
        "comments": comments,
        "songs": [s.title for s in playlist.songs],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    _save_feedback(feedback, feedback_path)
    print(f"\n  Thanks! Rating {rating}/5 saved.\n")
    return feedback


def _prompt_rating() -> int:
    while True:
        raw = input("  Rate this playlist (1–5): ").strip()
        if raw.isdigit() and 1 <= int(raw) <= 5:
            return int(raw)
        print("  Please enter a number between 1 and 5.")


def _save_feedback(feedback: dict, path: Optional[Path] = None) -> None:
    target = path or _DEFAULT_FEEDBACK_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "a", encoding="utf-8") as f:
        f.write(json.dumps(feedback) + "\n")


def load_feedback(feedback_path: Optional[Path] = None) -> list[dict]:
    """Return all stored human feedback entries."""
    path = feedback_path or _DEFAULT_FEEDBACK_PATH
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def average_rating(feedback_path: Optional[Path] = None) -> float:
    """Return the average human rating across all stored feedback."""
    entries = load_feedback(feedback_path)
    if not entries:
        return 0.0
    return round(sum(e["rating"] for e in entries) / len(entries), 2)
