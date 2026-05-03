from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

from src.logger import common_issues, load_logs, score_trends
from src.models import Song, UserInput, load_catalog
from src.pipeline import run_recommendation_pipeline


ROOT = Path(__file__).parent

PRESET_PROFILES: dict[str, dict] = {
    "Chill lofi focus": {
        "query": "chill lofi beats for focus",
        "mood": "chill",
        "preferences": ["relaxed", "focused"],
        "favorite_genre": "lofi",
        "target_energy": 0.38,
        "likes_acoustic": True,
        "danceability_preference": 0.55,
        "min_tempo_bpm": 60,
        "max_tempo_bpm": 95,
    },
    "High energy workout": {
        "query": "high energy workout",
        "mood": "intense",
        "preferences": ["energetic", "aggressive"],
        "favorite_genre": "pop",
        "target_energy": 0.92,
        "likes_acoustic": False,
        "danceability_preference": 0.88,
        "min_tempo_bpm": 110,
        "max_tempo_bpm": 150,
    },
    "Deep rock drive": {
        "query": "deep intense rock for a long drive",
        "mood": "intense",
        "preferences": ["aggressive"],
        "favorite_genre": "rock",
        "target_energy": 0.90,
        "likes_acoustic": False,
        "danceability_preference": 0.60,
        "min_tempo_bpm": 130,
        "max_tempo_bpm": 180,
    },
    "Romantic dinner": {
        "query": "romantic soul for a dinner evening",
        "mood": "romantic",
        "preferences": ["relaxed"],
        "favorite_genre": "soul",
        "target_energy": 0.48,
        "likes_acoustic": True,
        "danceability_preference": 0.65,
        "min_tempo_bpm": 80,
        "max_tempo_bpm": 115,
    },
    "Custom": {
        "query": "late night study music with a calm mood",
        "mood": "focused",
        "preferences": ["chill", "peaceful"],
        "favorite_genre": "lofi",
        "target_energy": 0.35,
        "likes_acoustic": True,
        "danceability_preference": 0.50,
        "min_tempo_bpm": 60,
        "max_tempo_bpm": 100,
    },
}


@st.cache_data
def get_catalog() -> list[Song]:
    return load_catalog()


def catalog_frame(catalog: list[Song]) -> pd.DataFrame:
    return pd.DataFrame([song.to_dict() for song in catalog])


def build_user_input(values: dict) -> UserInput:
    preferences = [
        item.strip()
        for item in values["preferences_text"].split(",")
        if item.strip()
    ]
    min_tempo = values["tempo_range"][0] if values["use_tempo"] else None
    max_tempo = values["tempo_range"][1] if values["use_tempo"] else None
    danceability = values["danceability"] if values["use_danceability"] else None

    return UserInput(
        mood=values["mood"].strip(),
        query=values["query"].strip(),
        preferences=preferences,
        favorite_genre=values["favorite_genre"].strip(),
        target_energy=values["target_energy"],
        likes_acoustic=values["likes_acoustic"],
        danceability_preference=danceability,
        min_tempo_bpm=min_tempo,
        max_tempo_bpm=max_tempo,
    )


def render_score(label: str, value: float, help_text: str) -> None:
    st.metric(label, f"{value:.2f}/10", help=help_text)


def render_playlist(songs: list[Song]) -> None:
    for index, song in enumerate(songs, start=1):
        with st.container(border=True):
            top, details = st.columns([2.5, 1.5], vertical_alignment="center")
            with top:
                st.subheader(f"{index}. {song.title}")
                st.caption(f"{song.artist} | {song.genre} | {song.mood}")
            with details:
                st.progress(song.energy, text=f"Energy {song.energy:.2f}")
                st.progress(song.danceability, text=f"Danceability {song.danceability:.2f}")
            st.caption(
                f"{song.tempo_bpm:.0f} BPM | Valence {song.valence:.2f} | "
                f"Acousticness {song.acousticness:.2f}"
            )


def render_analytics() -> None:
    logs = load_logs()
    if not logs:
        st.info("No saved runs yet. Generate a playlist to start tracking results.")
        return

    trends = score_trends(logs)
    issues = common_issues(logs)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Runs", trends["total_runs"])
    c2.metric("Avg reliability", f"{trends['avg_reliability']:.2f}/10")
    c3.metric("Avg iterations", f"{trends['avg_iterations']:.2f}")
    c4.metric("Failure rate", f"{trends['failure_rate'] * 100:.1f}%")

    if issues:
        st.write("Most common issues")
        st.dataframe(
            pd.DataFrame(issues, columns=["Issue", "Count"]),
            hide_index=True,
            use_container_width=True,
        )


def main() -> None:
    st.set_page_config(
        page_title="AudioVerse AI Music Studio",
        layout="wide",
    )

    st.title("AudioVerse AI Music Studio")
    st.caption("Generate an evaluated playlist from mood, genre, energy, and tempo controls.")

    catalog = get_catalog()
    catalog_df = catalog_frame(catalog)
    genres = sorted(catalog_df["genre"].unique())
    moods = sorted(catalog_df["mood"].unique())

    with st.sidebar:
        st.header("Generation Controls")
        preset_name = st.selectbox("Preset", list(PRESET_PROFILES.keys()))
        preset = PRESET_PROFILES[preset_name]

        query = st.text_area("Intent", value=preset["query"], height=96)
        mood = st.selectbox(
            "Mood",
            moods,
            index=moods.index(preset["mood"]) if preset["mood"] in moods else 0,
        )
        favorite_genre = st.selectbox(
            "Genre",
            genres,
            index=genres.index(preset["favorite_genre"])
            if preset["favorite_genre"] in genres
            else 0,
        )
        preferences_text = st.text_input(
            "Extra vibe tags",
            value=", ".join(preset["preferences"]),
        )
        target_energy = st.slider(
            "Energy",
            min_value=0.0,
            max_value=1.0,
            value=float(preset["target_energy"]),
            step=0.01,
        )
        likes_acoustic = st.toggle("Prefer acoustic texture", value=preset["likes_acoustic"])

        use_danceability = st.toggle("Use danceability target", value=True)
        danceability = st.slider(
            "Danceability",
            min_value=0.0,
            max_value=1.0,
            value=float(preset["danceability_preference"]),
            step=0.01,
            disabled=not use_danceability,
        )

        use_tempo = st.toggle("Use tempo range", value=True)
        tempo_range = st.slider(
            "Tempo BPM",
            min_value=50,
            max_value=190,
            value=(int(preset["min_tempo_bpm"]), int(preset["max_tempo_bpm"])),
            disabled=not use_tempo,
        )

        playlist_size = st.slider("Playlist size", 3, 8, 5)
        threshold = st.slider("Reliability threshold", 5.0, 9.5, 7.5, 0.1)
        max_iterations = st.slider("Refinement passes", 0, 3, 2)

        generate = st.button("Generate Playlist", type="primary", use_container_width=True)

    has_llm_key = bool(os.environ.get("GEMINI_API_KEY"))
    if not has_llm_key:
        st.warning(
            "GEMINI_API_KEY is not set. The app will still generate playlists, "
            "but the LLM critic will use its built-in fallback score."
        )

    tabs = st.tabs(["Generator", "Catalog", "Run History"])

    with tabs[0]:
        left, right = st.columns([1.2, 1], gap="large")
        with left:
            st.header("Playlist")
            if generate:
                values = {
                    "query": query,
                    "mood": mood,
                    "favorite_genre": favorite_genre,
                    "preferences_text": preferences_text,
                    "target_energy": target_energy,
                    "likes_acoustic": likes_acoustic,
                    "use_danceability": use_danceability,
                    "danceability": danceability,
                    "use_tempo": use_tempo,
                    "tempo_range": tempo_range,
                }
                user_input = build_user_input(values)
                with st.spinner("Generating and evaluating playlist..."):
                    playlist, evaluation = run_recommendation_pipeline(
                        user_input,
                        catalog=catalog,
                        k=playlist_size,
                        threshold=threshold,
                        max_iterations=max_iterations,
                        verbose=False,
                    )
                st.session_state["last_result"] = (playlist, evaluation)

            if "last_result" not in st.session_state:
                st.info("Choose a preset or adjust the controls, then generate a playlist.")
            else:
                playlist, evaluation = st.session_state["last_result"]
                render_playlist(playlist.songs)

        with right:
            st.header("Evaluation")
            if "last_result" in st.session_state:
                playlist, evaluation = st.session_state["last_result"]
                s1, s2, s3 = st.columns(3)
                with s1:
                    render_score("Reliability", evaluation.reliability_score, "Blended final score")
                with s2:
                    render_score("Heuristic", evaluation.heuristic_score, "Rule-based catalog metrics")
                with s3:
                    render_score("LLM critic", evaluation.llm_score, "Semantic playlist critique")

                if evaluation.issues:
                    st.error("Issues: " + ", ".join(evaluation.issues))
                else:
                    st.success("No refinement issues detected.")

                if evaluation.feedback:
                    st.write("Critic feedback")
                    for item in evaluation.feedback:
                        st.write(f"- {item}")

                if evaluation.heuristic_metrics:
                    st.write("Heuristic metrics")
                    st.dataframe(
                        pd.DataFrame(
                            evaluation.heuristic_metrics.items(),
                            columns=["Metric", "Value"],
                        ),
                        hide_index=True,
                        use_container_width=True,
                    )
            else:
                st.info("Evaluation details will appear after generation.")

    with tabs[1]:
        st.header("Catalog")
        col1, col2, col3 = st.columns(3)
        col1.metric("Songs", len(catalog_df))
        col2.metric("Genres", catalog_df["genre"].nunique())
        col3.metric("Artists", catalog_df["artist"].nunique())
        st.dataframe(catalog_df, hide_index=True, use_container_width=True)

    with tabs[2]:
        st.header("Run History")
        render_analytics()


if __name__ == "__main__":
    main()
