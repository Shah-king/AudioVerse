"""
LLM Critic — Module 3B.

Uses Claude to semantically evaluate a playlist against the user's intent.
Returns a score (0–10), a list of strengths/suggestions (feedback), and
a list of concrete issues that should trigger refinement.
"""
from __future__ import annotations

import json
import os
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import anthropic as _anthropic_type

from .models import Playlist, UserInput

_CLIENT: "anthropic.Anthropic | None" = None  # type: ignore[name-defined]
MODEL = "claude-haiku-4-5-20251001"

# Cached prompt template — populated once and kept warm across calls
_SYSTEM_PROMPT = """\
You are an expert music curator and playlist evaluator.
Your job is to critically assess whether a generated playlist truly serves \
the user's stated intent. Be honest and specific — reference actual song \
titles, artists, and attributes in your evaluation.
"""

_USER_TEMPLATE = """\
## User Request
- **Mood / Vibe**: {mood}
- **Query**: "{query}"
- **Preferences**: {preferences}

## Generated Playlist ({n} songs)
{playlist_summary}

## Scoring Rubric
Evaluate each dimension from 0–10 then output a single weighted score:
| Dimension            | Weight | What to assess                                  |
|----------------------|--------|-------------------------------------------------|
| Mood Alignment       |  40%   | Do songs match the requested mood & emotion?    |
| Consistency of Vibe  |  35%   | Does the playlist feel cohesive end-to-end?     |
| Thematic Coherence   |  25%   | Do genre/tempo/energy form a unified experience?|

## Required Output Format
Respond ONLY with valid JSON — no markdown fences, no extra text:
{{
  "score": <float 0–10>,
  "strengths": ["<specific strength>", ...],
  "issues": ["<specific issue>", ...],
  "suggestions": ["<actionable suggestion>", ...]
}}

Common issue tags to use when relevant (use these exact strings so the \
refiner can parse them):
  "mood_mismatch"       — playlist doesn't match the requested mood
  "low_diversity"       — too many songs from the same artist/genre
  "energy_mismatch"     — energy level doesn't fit the query
  "incoherent_vibe"     — songs clash tonally
  "low_novelty"         — playlist is too predictable
"""


def _get_client():
    global _CLIENT
    if _CLIENT is None:
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "anthropic package is required. Install it with: pip install anthropic"
            ) from exc
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY is not set. "
                "Export it before running the pipeline."
            )
        _CLIENT = anthropic.Anthropic(api_key=api_key)
    return _CLIENT


def _parse_response(raw: str) -> dict:
    """Extract the JSON object from the model response robustly."""
    # Strip any accidental markdown fences
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    # Find the first {...} block
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM response:\n{raw}")
    return json.loads(match.group())


def evaluate_with_llm(
    user_input: UserInput,
    playlist: Playlist,
) -> tuple[float, list[str], list[str]]:
    """
    Call the LLM critic and return:
      (score: float, feedback: list[str], issues: list[str])

    feedback combines strengths + suggestions.
    issues are the actionable problem tags.
    """
    prompt = _USER_TEMPLATE.format(
        mood=user_input.mood,
        query=user_input.query,
        preferences=(
            ", ".join(user_input.preferences)
            if user_input.preferences
            else "none specified"
        ),
        n=len(playlist.songs),
        playlist_summary=playlist.summary(),
    )

    response = _get_client().messages.create(
        model=MODEL,
        max_tokens=600,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text
    data = _parse_response(raw)

    score = max(0.0, min(10.0, float(data.get("score", 5.0))))
    feedback = data.get("strengths", []) + data.get("suggestions", [])
    issues = data.get("issues", [])

    return round(score, 2), feedback, issues
