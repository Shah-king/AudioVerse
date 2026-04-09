"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

from pathlib import Path
from recommender import load_songs, recommend_songs

DATA_PATH = Path(__file__).parent.parent / "data" / "songs.csv"


USER_PROFILES = {
    "High-Energy Pop": {
        "genre": "pop",
        "mood": "happy",
        "energy": 0.9,
        "danceability": 0.85,
    },
    "Chill Lofi": {
        "genre": "lofi",
        "mood": "chill",
        "energy": 0.35,
        "danceability": 0.5,
        "min_tempo_bpm": 60,
        "max_tempo_bpm": 95,
    },
    "Deep Intense Rock": {
        "genre": "rock",
        "mood": "intense",
        "energy": 0.92,
        "danceability": 0.55,
        "min_tempo_bpm": 130,
        "max_tempo_bpm": 180,
    },

    # --- Edge case profiles ---

    # 1. Genre exists, mood does not exist in the dataset at all.
    #    No song will ever earn the +1.0 mood bonus.
    #    Max achievable score is 4.0. The system silently degrades
    #    without warning the user their mood preference is unmatched.
    "Ghost Mood": {
        "genre": "pop",
        "mood": "melancholic",       # no pop song has this mood
        "energy": 0.8,
    },

    # 2. Genre does not exist in the dataset at all.
    #    The +2.0 genre bonus is permanently unreachable.
    #    Every song starts at 0 — recommendations are driven
    #    entirely by energy, producing meaningless results.
    "Unknown Genre": {
        "genre": "metal",            # not in songs.csv
        "mood": "intense",
        "energy": 0.95,
    },

    # 3. Extreme low energy (0.0). The closest song (Moonlit Symphony,
    #    energy 0.24) still loses 0.48 pts on energy alone.
    #    High-energy songs are not heavily punished enough —
    #    a rock song at 0.91 only loses 1.82 pts, still competitive
    #    against genre/mood mismatches.
    "Dead Silent": {
        "genre": "ambient",
        "mood": "chill",
        "energy": 0.0,
    },

    # 4. Conflicting preferences: user wants sad/melancholic mood
    #    but maximum energy. No song in the dataset combines
    #    high energy with a melancholic mood. The scorer will
    #    award energy points to aggressive/intense songs that
    #    feel nothing like what the user described.
    "Sad Headbanger": {
        "genre": "indie rock",
        "mood": "melancholic",
        "energy": 1.0,
    },

    # 5. Energy exactly 0.5 (the midpoint). Every song on the
    #    0–1 scale is within 0.5 of this value, so energy similarity
    #    never drops below 1.0 pts. The energy feature stops
    #    differentiating songs — genre/mood dominate completely,
    #    and songs with wildly different feels score very similarly.
    "Dead Average": {
        "genre": "jazz",
        "mood": "relaxed",
        "energy": 0.5,
    },

    # 6. Impossibly tight tempo window (1 BPM range).
    #    Almost no song will fall inside [99, 100] BPM,
    #    so the +0.5 tempo bonus never fires for anyone.
    #    Silently ignored — no error, just missing points.
    "BPM Perfectionist": {
        "genre": "electronic",
        "mood": "energetic",
        "energy": 0.92,
        "min_tempo_bpm": 99,
        "max_tempo_bpm": 100,
    },
}


def print_recommendations(recommendations: list, user_prefs: dict, label: str = "") -> None:
    """Prints a clean, readable summary of the top-k recommendations."""
    width = 52

    print("\n" + "=" * width)
    print(f"  {label}" if label else "  Music Recommendations")
    print(f"  Genre: {user_prefs.get('genre','?')}  |  "
          f"Mood: {user_prefs.get('mood','?')}  |  "
          f"Energy: {user_prefs.get('energy','?')}")
    print("=" * width)

    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"\n  #{rank}  {song['title']}  -  {song['artist']}")
        print(f"       Score: {score:.2f} / 6.0")
        print(f"       Why:   ", end="")

        # Print each reason on its own indented line
        reasons = explanation.split("; ")
        print(reasons[0])
        for reason in reasons[1:]:
            print(f"              {reason}")

    print("\n" + "=" * width + "\n")


def main() -> None:
    songs = load_songs(str(DATA_PATH))
    print(f"Loaded songs: {len(songs)}")

    for label, user_prefs in USER_PROFILES.items():
        recommendations = recommend_songs(user_prefs, songs, k=5)
        print_recommendations(recommendations, user_prefs, label)


if __name__ == "__main__":
    main()
