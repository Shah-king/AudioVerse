# AI Music Recommender with Self-Critique Loop

A content-based music recommendation system that evaluates and iteratively refines its own playlists using a dual-scoring pipeline — combining rule-based heuristics with a live Gemini LLM critic.

---

## Portfolio

**GitHub:** [https://github.com/Shahriar-ferdous/applied-ai-system-project](https://github.com/Shahriar-ferdous/applied-ai-system-project)

**Loom Walkthrough:** *(add your Loom link here after recording)*

### What this project says about me as an AI engineer

This project reflects my ability to think beyond the initial solution and ask harder questions — not just "does it recommend songs?" but "how do we know the recommendations are good, and what happens when they aren't?" Designing a self-critique loop required me to treat evaluation as a first-class engineering problem, not an afterthought. Working through real failures — LLM quota errors, malformed JSON, a refiner that produced confidently wrong results — taught me that robust AI systems are built at the seams between components, not just within them. I am an engineer who ships working systems, debugs them against real API behavior, and builds in the fallbacks and observability that make AI trustworthy in practice.

---

## Original Project (Modules 1–3): AudioVerse

The original project, **AudioVerse**, was a rule-based music recommender built in Modules 1–3. It scored songs against a user profile using a 6.5-point rubric (genre match, mood, energy similarity, tempo, danceability, acousticness) and applied a diversity reranker to penalize repeated artists and genres. AudioVerse demonstrated how content-based filtering works without any machine learning — every recommendation was fully explainable by a point breakdown. Its limitations were a fixed scoring formula with no feedback loop and no semantic understanding of *why* a playlist felt right or wrong.

---

## Title and Summary

**AI Music Recommender with Self-Critique Loop** extends AudioVerse into a full agentic pipeline. After generating an initial playlist, the system evaluates it twice — once with fast heuristic metrics (diversity, novelty, energy balance) and once with a Gemini LLM that scores mood alignment, vibe consistency, and thematic coherence. If the combined reliability score falls below 7.5/10 or the LLM flags specific issues, a refinement agent adjusts the retrieval parameters and regenerates the playlist — up to 2 times. Every run is logged to JSONL for analytics.

This matters because most recommender systems are black boxes. This pipeline makes quality evaluation explicit, auditable, and self-correcting.

---

## Architecture Overview

```
UserInput (mood, query, genre, energy)
    |
    v
[Module 2] Recommendation Engine
    Hybrid scoring: content rules + cosine similarity on 5-dim embeddings
    Diversity reranker: penalizes repeated artists/genres
    |
    v
Initial Playlist (k=5 songs)
    |
    +---> [Module 3A] Heuristic Evaluator
    |         diversity_score, genre_spread, novelty_score,
    |         repetition_penalty, popularity_balance  --> score [0-10]
    |
    +---> [Module 3B] LLM Critic (Gemini 2.5 Flash)
              Structured JSON rubric:
                Mood Alignment (40%) + Vibe Consistency (35%) + Thematic Coherence (25%)
              Returns score, strengths, issues, suggestions
    |
    v
[Module 4] Aggregator
    reliability_score = 0.5 * heuristic_score + 0.5 * llm_score
    |
    v
Should refine? (reliability < 7.5 OR issues non-empty)
    |
   YES --> [Module 5] Refiner Agent
    |         - Exclude off-genre/off-mood songs
    |         - Exclude repeated artists
    |         - Boost mood weight in preferences
    |         - Nudge target_energy based on detected issues
    |         - Re-run recommendation engine on filtered catalog
    |         (max 2 iterations, then loop back to evaluation)
    |
   NO  --> [Module 6] Logger
               Appends run to logs/pipeline.jsonl
    |
    v
Final Playlist + EvaluationResult
```

---

## Setup Instructions

### 1. Clone and navigate

```bash
cd applied-ai-system-project
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Requirements: `google-genai`, `pandas`, `pytest`, `python-dotenv`

### 3. Set your Gemini API key

```bash
cp .env.example .env
```

Edit `.env` and add your key:

```
GEMINI_API_KEY=your_key_here
```

Get a free key at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey). A paid account is recommended for consistent LLM scoring (free-tier quota is very limited).

### 4. Run a demo profile

```bash
python -m src.run_pipeline --profile chill_lofi
```

Available profiles:

| Profile | Mood | Query |
|---|---|---|
| `chill_lofi` | chill | chill lofi beats for focus |
| `sad_hopeful` | melancholic | sad but hopeful songs for late night study |
| `high_energy_workout` | intense | high energy workout |
| `deep_rock` | intense | deep intense rock for a long drive |
| `romantic_evening` | romantic | romantic soul for a dinner evening |

### 5. Optional flags

```bash
python -m src.run_pipeline --profile deep_rock --feedback   # rate the playlist 1-5
python -m src.run_pipeline --analytics                      # view score trends from past runs
```

### 6. Run tests

```bash
python -m pytest tests/test_pipeline.py -v
```

---

## Sample Interactions

### Example 1 — Chill Lofi (no refinement needed)

**Input:**
```
Profile  : chill_lofi
Query    : "chill lofi beats for focus"
Mood     : chill | Genre: lofi | Energy: 0.38
```

**Initial Playlist:**
```
1. Focus Flow          LoRoom           [lofi | focused]
2. Library Rain        Paper Lanterns   [lofi | chill]
3. Midnight Coding     LoRoom           [lofi | chill]
4. Rain Study Session  Hazy Tape        [lofi | focused]
5. Soft Glow           Pastel Fog       [lofi | chill]
```

**Evaluation:**
```
Heuristic  :  8.20/10  (diversity=0.80, genre_spread=1.00, novelty=1.00)
LLM score  :  8.40/10
Reliability:  8.30/10
Strengths  : Strong lofi genre cohesion throughout.
             All tracks support a focused, calm study atmosphere.
[OK] Reliability 8.30/10 >= 7.5 -- stopping.
```

---

### Example 2 — Deep Rock (refinement triggered)

**Input:**
```
Profile  : deep_rock
Query    : "deep intense rock for a long drive"
Mood     : intense | Genre: rock | Energy: 0.90 | Tempo: 130-180 BPM
```

**Initial Playlist:** Mixed rock and non-rock songs with lower-energy tracks included.

**LLM Issues detected:** `mood_mismatch`, `energy_mismatch`

**After Refinement (iteration 1):**
```
1. Storm Runner        Voltline         [rock | intense]
2. Gym Hero            Max Pulse        [pop  | intense]
3. Electric Pulse      Synthesize       [electronic | energetic]
4. Cipher Flow         Beat Merchant    [hip-hop | aggressive]
5. Night Drive Loop    Neon Echo        [synthwave | moody]
```

**Final Evaluation:**
```
Heuristic  :  8.50/10
LLM score  :  8.10/10
Reliability:  8.30/10
Iterations :  1
```

---

### Example 3 — Sad Hopeful

**Input:**
```
Profile  : sad_hopeful
Query    : "sad but hopeful songs for late night study"
Mood     : melancholic | Genre: lofi | Energy: 0.35
```

**Output Playlist:**
```
1. Moonlit Symphony    Classical Echoes   [classical | melancholic]
2. Late Night Pages    Velvet Desk        [lofi | focused]
3. Quiet Hours         Still Frame        [lofi | peaceful]
4. Soft Glow           Pastel Fog         [lofi | chill]
5. Library Rain        Paper Lanterns     [lofi | chill]
```

**LLM Feedback:**
```
Strengths  : Excellent low-energy cohesion for late-night atmosphere.
             Acoustic-heavy selection supports emotional introspection.
Reliability: 8.05/10 -- no refinement needed.
```

---

## Design Decisions

### Dual evaluation (heuristic + LLM)
A single LLM score would be expensive, slow, and opaque. A single heuristic score misses semantic qualities like "does this *feel* like a long drive?" Combining both at 50/50 gives speed and explainability from the heuristic side, and semantic nuance from the LLM side. **Trade-off:** equal weighting is arbitrary; a tuned weighting based on user feedback data would be better.

### Graceful LLM fallback
If the Gemini API fails (quota, network, key error), the system returns a neutral 7.5 fallback score instead of crashing. The pipeline continues in heuristic-only mode. **Trade-off:** a failing API silently produces lower-quality results; a future improvement would surface a clearer warning in the final output.

### Refinement excludes only bad songs
Early versions excluded all songs from the current playlist to force fresh picks. This backfired with a small catalog — the refiner ran out of genre-appropriate options and returned completely off-topic songs (reggae instead of lofi). The fix: only exclude songs with wrong genre/mood and artists causing repetition issues; good songs remain eligible for re-selection. **Trade-off:** the refined playlist may overlap with the original, but overlap with good songs is acceptable.

### Small static catalog (38 songs)
The catalog is hand-crafted CSV data, not a real music database. This keeps the project self-contained and reproducible without third-party API keys. **Trade-off:** recommendation diversity is limited; in production this would connect to a Spotify or MusicBrainz API.

### Content-based only (no collaborative filtering)
No user-user similarity or implicit feedback signals are used. Every recommendation is explainable by song features alone, which is appropriate for a classroom demonstration. **Trade-off:** no personalization that improves over time with usage.

---

## Reliability and Evaluation

### How the system proves it works

The system uses four complementary reliability mechanisms:

**1. Automated unit tests**
23 tests across 5 test classes run offline using mocked LLM responses. They cover every module independently — evaluator metrics, aggregator score blending, refiner trigger logic, recommendation engine ranking, and full end-to-end scenarios.

```
23 out of 23 tests passed. The refiner correctly triggered on low scores and
non-empty issue lists in all mocked scenarios. Energy and diversity constraints
held across all 4 recommendation engine tests.
```

Run them yourself:
```bash
python -m pytest tests/test_pipeline.py -v
```

**2. Reliability / confidence scoring**
Every pipeline run produces a `reliability_score` — a 0–10 confidence value computed as:

```
reliability_score = 0.5 * heuristic_score + 0.5 * llm_score
```

The heuristic score is fully deterministic (no API needed). The LLM score adds semantic confidence. Across all 5 demo profiles the reliability scores ranged from **7.39 to 8.67 / 10**. The system only accepts the playlist when this score exceeds 7.5 — otherwise it refines automatically.

**3. Logging and error handling**
Every pipeline run is appended to `logs/pipeline.jsonl` with the full input, initial playlist, refined playlist, both scores, issue tags, feedback, and iteration count. LLM failures are caught and logged to stderr with a specific reason (quota exceeded, invalid key, empty response, JSON parse error). The pipeline never crashes — it degrades gracefully to heuristic-only mode.

View aggregated stats from all past runs:
```bash
python -m src.run_pipeline --analytics
```

**4. Human evaluation**
An optional `--feedback` flag prompts a 1–5 star rating and free-text comment after each run, stored in `logs/human_feedback.jsonl` for future weight calibration.

```bash
python -m src.run_pipeline --profile chill_lofi --feedback
```

---

### Testing Summary

### What worked

- **23 unit tests pass** covering the heuristic evaluator, aggregator, refiner logic, recommendation engine, and mocked end-to-end scenarios.
- Mocking the LLM with `unittest.mock.patch` let all tests run offline with no API cost and fully deterministic results.
- The heuristic evaluator correctly penalizes repeated artists and detects `low_diversity`, `high_repetition`, and `low_novelty` tags.
- The aggregator correctly merges issue lists from both evaluators without duplicates.
- The refiner correctly triggers on both low reliability score and non-empty issues.

### What didn't work (and was fixed)

| Problem | Fix |
|---|---|
| `UnicodeEncodeError` on Windows (cp1252) | Replaced all box-drawing/special characters with ASCII equivalents in pipeline output |
| `ModuleNotFoundError: anthropic` during test collection | Switched to lazy import inside `_get_client()`; removed Anthropic dependency entirely |
| OpenAI `RateLimitError 429` | Switched LLM backend from OpenAI to Google Gemini |
| `google.generativeai` deprecation warning | Migrated to new `google-genai` SDK (`from google import genai`) |
| Gemini response truncated mid-JSON | Removed `max_output_tokens` cap; let the model respond fully |
| Gemini returning trailing commas in JSON | Added regex cleanup before parsing: `re.sub(r",\s*([}\]])", r"\1", ...)` |
| Refined playlist returning completely off-genre songs | Expanded catalog from 18 to 38 songs; fixed refiner to only exclude bad-fit songs instead of the entire current playlist |
| Heuristic over-rewarding diverse-but-wrong playlists | A wildly off-topic refined playlist scored 9.84 heuristically (perfect diversity). Confirmed that semantic correctness requires the LLM critic — heuristics alone are insufficient |

### What was learned

Heuristic diversity scoring can reward the *wrong* outcome. A refined playlist that replaced all lofi songs with reggae, classical, and country scored a near-perfect 9.84 heuristically because every song was a different genre. The LLM critic exists precisely to catch this — quantitative metrics can be gamed in ways that semantic evaluation cannot.

---

## Responsible AI Reflection

### Limitations and biases

The system has several embedded biases worth naming honestly:

- **Genre gatekeeping.** The recommendation engine awards a hard +2.0 bonus for an exact genre match. A jazz song with a perfect lofi feel scores lower than a mediocre lofi track. Genre labels are a proxy for sound, not a guarantee of it.
- **Catalog bias.** The 38-song catalog was hand-curated. Genres like lofi and ambient are over-represented, while others (Latin, R&B, classical) have one or zero entries. Any user preference outside the catalog's coverage will produce poor results — the system cannot recommend what it has never seen.
- **Mood vocabulary mismatch.** User moods and song moods are compared as plain strings. "Hopeful" and "peaceful" are semantically similar but score zero match. The system has no synonym awareness unless the LLM critic catches it.
- **LLM subjectivity.** The Gemini critic evaluates playlists using its own training data about what "chill lofi" or "intense rock" means. Those associations reflect the biases in its training corpus — predominantly English-language, Western music culture.
- **Energy as a single float.** A track's energy is one number. Two songs can share the same energy value but feel completely different in context (a slow metal ballad vs. an ambient drone). The system cannot capture that nuance.

### Could this AI be misused?

The system is low-stakes — it recommends songs from a fixed local catalog, logs to a local file, and calls a public LLM API. Direct harm potential is minimal. However, scaled-up versions of this pattern raise real concerns:

- A production recommender with user listening history could build detailed behavioral profiles without users knowing.
- The LLM critic could be prompted to evaluate content other than music if the input validation is weak.
- Automated refinement loops without human oversight could drift toward optimizing metrics that don't reflect what users actually want.

Mitigations built into this project: no personal data is collected, logs contain only query text and song metadata, and the human feedback mechanism is opt-in via an explicit `--feedback` flag.

### What surprised me during reliability testing

The most surprising finding was that **a high heuristic score could mean the playlist was completely wrong**. When the refiner excluded all lofi songs due to artist repetition and the catalog ran out of good alternatives, the refined playlist (reggae, classical, country, soul) scored 9.84/10 heuristically — a near-perfect score — because every song was from a different artist and genre, satisfying the diversity metric perfectly. The system would have accepted that playlist as its best work without the LLM critic to flag the mood and genre mismatch.

This revealed that individual metrics can be individually correct and collectively misleading. Diversity *is* good — but not when it comes at the cost of relevance. No single number captures playlist quality.

---

## Reflection

Building this system taught me that **evaluation is as hard as generation**. Filtering songs by genre and energy is straightforward. Judging whether a playlist *coheres* — whether the transition from song 3 to song 4 preserves the vibe the user asked for — requires the kind of semantic understanding that only an LLM can approximate.

The self-critique loop pattern (generate → evaluate → refine → repeat) is a practical version of what modern AI systems do internally, such as RLHF and chain-of-thought verification. Implementing it from scratch made the concept concrete: you need a quality signal, a way to act on that signal, and a stopping condition. Getting all three right took more iteration than writing the recommender itself.

The biggest insight was about **failure modes at the boundary between components**. Each module worked correctly in isolation. The failures happened at the interfaces: the refiner trusted the evaluator's issue tags and acted on them too aggressively; the LLM's verbose output overflowed a token budget set for a smaller model; the JSON parser assumed well-formed output from a model that occasionally adds trailing commas. Robust AI systems need as much engineering at the seams as at the core.

Finally, working with a paid API changes the development experience significantly. Fallback logic that masked real failures made the pipeline *appear* to work (returning neutral 7.5 scores) when the LLM was silently down. The lesson: always verify that your LLM is actually being called and returning meaningful output before declaring the system functional.

---

## AI Collaboration

Throughout this project I used Claude (an AI assistant) to help architect, implement, and debug the system. The collaboration was genuinely iterative — not just code generation, but back-and-forth diagnosis when things broke.

**One helpful suggestion: human feedback collection with persistent storage.**
Claude proposed adding an optional `--feedback` flag that prompts the user for a 1–5 star rating and free-text comment after each run, storing responses in `logs/human_feedback.jsonl`. This was a suggestion I had not planned for. It added a real evaluation dimension — beyond automated metrics and LLM scores, there is now a place to capture what a real listener actually thought of the playlist. This data could be used in future iterations to recalibrate the 50/50 heuristic/LLM weighting toward whatever dimension users actually care about most.

**One flawed suggestion: the initial JSON parsing approach.**
When the LLM critic was first implemented, the response parser simply stripped markdown fences and ran `json.loads()` on whatever text the model returned. This worked in testing but broke in production because Gemini 2.5 Flash occasionally returns trailing commas in JSON arrays — valid in JavaScript, invalid in Python's `json` module. The initial code had no handling for this, and the first real API response caused a `JSONDecodeError` that sent the pipeline into fallback mode. The fix required adding a regex cleanup step (`re.sub(r",\s*([}\]])", r"\1", ...)`) before parsing. The suggestion to parse the response that way was technically reasonable but did not account for how real LLM outputs deviate from strict JSON spec. It took a live failure to surface the gap.
