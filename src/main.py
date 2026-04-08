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


def print_recommendations(recommendations: list, user_prefs: dict) -> None:
    """Prints a clean, readable summary of the top-k recommendations."""
    width = 52

    print("\n" + "=" * width)
    print(f"  Music Recommendations")
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

    user_prefs = {"genre": "pop", "mood": "happy", "energy": 0.8}

    recommendations = recommend_songs(user_prefs, songs, k=5)
    print_recommendations(recommendations, user_prefs)


if __name__ == "__main__":
    main()
