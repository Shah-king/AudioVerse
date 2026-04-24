"""
CLI entry point for the AI Music Recommender with Self-Critique Loop.

Usage:
    python -m src.run_pipeline
    python -m src.run_pipeline --analytics

Requires OPENAI_API_KEY in environment or .env file.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Load .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

from .logger import print_analytics
from .models import UserInput, load_catalog
from .pipeline import run_recommendation_pipeline

# ---------------------------------------------------------------------------
# Demo profiles
# ---------------------------------------------------------------------------

DEMO_PROFILES: dict[str, UserInput] = {
    "high_energy_workout": UserInput(
        mood="intense",
        query="high energy workout",
        preferences=["energetic", "aggressive"],
        favorite_genre="pop",
        target_energy=0.92,
        likes_acoustic=False,
        danceability_preference=0.88,
    ),
    "sad_hopeful": UserInput(
        mood="melancholic",
        query="sad but hopeful songs for late night study",
        preferences=["chill", "focused"],
        favorite_genre="lofi",
        target_energy=0.35,
        likes_acoustic=True,
    ),
    "chill_lofi": UserInput(
        mood="chill",
        query="chill lofi beats for focus",
        preferences=["relaxed", "focused"],
        favorite_genre="lofi",
        target_energy=0.38,
        likes_acoustic=True,
        min_tempo_bpm=60,
        max_tempo_bpm=95,
    ),
    "deep_rock": UserInput(
        mood="intense",
        query="deep intense rock for a long drive",
        preferences=["aggressive"],
        favorite_genre="rock",
        target_energy=0.90,
        likes_acoustic=False,
        min_tempo_bpm=130,
        max_tempo_bpm=180,
    ),
    "romantic_evening": UserInput(
        mood="romantic",
        query="romantic soul for a dinner evening",
        preferences=["relaxed"],
        favorite_genre="soul",
        target_energy=0.48,
        likes_acoustic=True,
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Music Recommender with Self-Critique Loop"
    )
    parser.add_argument(
        "--profile",
        choices=list(DEMO_PROFILES.keys()),
        default="chill_lofi",
        help="Demo user profile to run (default: chill_lofi)",
    )
    parser.add_argument(
        "--analytics",
        action="store_true",
        help="Print analytics summary from past runs and exit",
    )
    parser.add_argument(
        "--feedback",
        action="store_true",
        help="Prompt for human feedback after the recommendation",
    )
    args = parser.parse_args()

    if args.analytics:
        print_analytics()
        return

    if not os.environ.get("GEMINI_API_KEY"):
        print(
            "\n[ERROR] GEMINI_API_KEY is not set.\n"
            "  Copy .env.example to .env and add your key, or:\n"
            "  export GEMINI_API_KEY=your_key_here\n"
            "  Get a free key at: https://aistudio.google.com/app/apikey\n"
        )
        sys.exit(1)

    user_input = DEMO_PROFILES[args.profile]
    catalog = load_catalog()

    print(f"\n  Profile  : {args.profile}")
    print(f"  Query    : \"{user_input.query}\"")
    print(f"  Mood     : {user_input.mood}")
    print(f"  Genre    : {user_input.favorite_genre}")
    print(f"  Energy   : {user_input.target_energy}")

    playlist, evaluation = run_recommendation_pipeline(
        user_input,
        catalog=catalog,
        verbose=True,
    )

    if args.feedback:
        from .human_feedback import collect_user_feedback
        collect_user_feedback(playlist)


if __name__ == "__main__":
    main()
