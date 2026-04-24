"""
LLM Critic — Module 3B.

Uses Google Gemini to semantically evaluate a playlist against the user's intent.
Returns a score (0-10), a list of strengths/suggestions (feedback), and
a list of concrete issues that should trigger refinement.
"""
from __future__ import annotations

import json
import os
import re

from .models import Playlist, UserInput

_CLIENT = None
MODEL = "gemini-2.5-flash"

_SYSTEM_PROMPT = """\
You are an expert music curator and playlist evaluator.
Your job is to critically assess whether a generated playlist truly serves \
the user's stated intent. Be honest and specific -- reference actual song \
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
Evaluate each dimension from 0-10 then output a single weighted score:
| Dimension            | Weight | What to assess                                  |
|----------------------|--------|-------------------------------------------------|
| Mood Alignment       |  40%   | Do songs match the requested mood & emotion?    |
| Consistency of Vibe  |  35%   | Does the playlist feel cohesive end-to-end?     |
| Thematic Coherence   |  25%   | Do genre/tempo/energy form a unified experience?|

## Required Output Format
Respond ONLY with valid JSON -- no markdown fences, no code blocks, no extra text before or after.
Keep each string value under 20 words. Output format:
{{
  "score": <float 0-10>,
  "strengths": ["<specific strength>", ...],
  "issues": ["<specific issue>", ...],
  "suggestions": ["<actionable suggestion>", ...]
}}

Common issue tags to use when relevant (use these exact strings so the \
refiner can parse them):
  "mood_mismatch"       -- playlist doesn't match the requested mood
  "low_diversity"       -- too many songs from the same artist/genre
  "energy_mismatch"     -- energy level doesn't fit the query
  "incoherent_vibe"     -- songs clash tonally
  "low_novelty"         -- playlist is too predictable
"""


def _get_client():
    global _CLIENT
    if _CLIENT is None:
        try:
            from google import genai
        except ImportError as exc:
            raise ImportError(
                "google-genai package is required. "
                "Install it with: pip install google-genai"
            ) from exc
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY is not set. "
                "Add it to your .env file or export it before running."
            )
        _CLIENT = genai.Client(api_key=api_key)
    return _CLIENT


def _parse_response(raw: str) -> dict:
    """Extract the JSON object from the model response robustly."""
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in LLM response:\n{raw}")
    # Strip trailing commas before closing brackets/braces (common LLM quirk)
    json_str = re.sub(r",\s*([}\]])", r"\1", match.group())
    return json.loads(json_str)


def evaluate_with_llm(
    user_input: UserInput,
    playlist: Playlist,
) -> tuple[float, list[str], list[str]]:
    """
    Call the Gemini LLM critic and return:
      (score: float, feedback: list[str], issues: list[str])

    Falls back to a neutral heuristic-only score if the API call fails
    (e.g. quota exceeded, no internet, invalid key).
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

    try:
        from google.genai import types
        client = _get_client()
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
            ),
        )
        raw = response.text
        if raw is None:
            # Fallback: extract from candidates directly
            raw = response.candidates[0].content.parts[0].text
        if not raw:
            raise ValueError("Empty response from Gemini")
        data = _parse_response(raw)

        score = max(0.0, min(10.0, float(data.get("score", 5.0))))
        feedback = data.get("strengths", []) + data.get("suggestions", [])
        issues = data.get("issues", [])
        return round(score, 2), feedback, issues

    except Exception as e:
        _print_llm_warning(e)
        return 7.5, [f"[LLM unavailable: {type(e).__name__}]"], []


def _print_llm_warning(error: Exception) -> None:
    import sys
    msg = str(error)
    if "quota" in msg.lower() or "429" in msg:
        reason = "Gemini quota exceeded - check your quota at aistudio.google.com"
    elif "api_key" in msg.lower() or "401" in msg:
        reason = "Invalid GEMINI_API_KEY -- check your .env file"
    else:
        reason = str(error)
    print(f"\n  [LLM WARNING] Falling back to heuristic-only scoring.\n"
          f"  Reason: {reason}\n", file=sys.stderr)
