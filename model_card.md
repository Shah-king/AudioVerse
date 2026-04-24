# Model Card: AI Music Recommender with Self-Critique Loop

---

## 1. Model Name

**AudioVerse 2.0** — a content-based music recommender extended with a dual-evaluation self-critique loop. The system generates playlists, scores them with both heuristic metrics and a live LLM critic, and automatically refines them when quality falls below threshold.

*Built on top of AudioVerse 1.0 (Modules 1–3), which was a point-based recommender without any evaluation or refinement capability.*

---

## 2. Intended Use

AudioVerse 2.0 generates top-5 song recommendations based on a user's stated mood, genre, energy level, and query. It then evaluates and iteratively improves those recommendations using a reliability scoring loop.

**Intended use:**
- Demonstrating self-critique and agentic refinement patterns in AI systems
- Learning how content-based filtering, LLM evaluation, and iterative agent loops work together
- Classroom and portfolio demonstrations

**Not intended for:**
- Real music discovery at production scale
- Users with niche, cross-genre, or culturally specific tastes outside the 48-song catalog
- Replacing streaming platforms with real listening history and collaborative filtering

The system assumes users can express their preferences as a mood, genre, and energy level. It does not learn from listening behavior over time.

---

## 3. How the Model Works

AudioVerse 2.0 is a seven-module pipeline. Here is how each part works in plain language:

### Step 1 — Recommendation Engine (Module 2)
Every song in the catalog gets a score based on how well it matches the user's request. The scoring has two layers:

**Content-based rules (up to ~6.5 points):**
- Genre match: +2.0 if the song's genre matches the user's preferred genre
- Mood match: +1.0 if the mood is in the user's preferences
- Energy similarity: up to +2.0 — the closer the song's energy to the user's target, the higher the bonus
- Danceability, tempo, and acousticness: up to +0.5 each for matching those preferences

**Embedding similarity (up to +1.0):**
Each song is represented as a 5-number vector (energy, valence, danceability, acousticness, normalized tempo). The user's preferences are turned into the same kind of vector, and cosine similarity adds a bonus for songs that are close in that feature space.

After scoring, a diversity reranker penalizes repeated artists (−1.0) and repeated genres (−0.5) so the final playlist has variety.

### Step 2 — Heuristic Evaluator (Module 3A)
Once a playlist is generated, it is evaluated without any AI. Five metrics are computed:
- **Diversity score** — what fraction of songs are from unique artists
- **Genre spread** — what fraction of songs are from unique genres
- **Novelty score** — what fraction of songs the user has not heard before
- **Repetition penalty** — how much any single artist dominates the list
- **Popularity balance** — whether the energy levels are centered or all extreme

These are combined into a single heuristic score out of 10.

### Step 3 — LLM Critic (Module 3B)
The playlist is sent to Google Gemini (gemini-2.5-flash) with a structured evaluation rubric:
- 40% — Mood Alignment: do the songs match the requested feeling?
- 35% — Consistency of Vibe: does the playlist hold together end-to-end?
- 25% — Thematic Coherence: does the genre/tempo/energy form a unified experience?

Gemini returns a score out of 10, a list of strengths, a list of actionable issue tags (such as `mood_mismatch` or `energy_mismatch`), and suggestions for improvement.

### Step 4 — Aggregation (Module 4)
The two scores are blended equally:
```
reliability_score = 0.5 × heuristic_score + 0.5 × llm_score
```

### Step 5 — Refinement Agent Loop (Module 5)
If the reliability score is below 7.5 out of 10, or if any issues were flagged, the refiner adjusts the parameters and re-generates the playlist:
- Songs with the wrong genre or mood are removed from the candidate pool
- Artists causing repetition are excluded
- If mood_mismatch was flagged, the mood is weighted more heavily in scoring
- If energy_mismatch was flagged, the target energy is nudged up or down

This loop runs up to 2 times. If the score improves past the threshold, it stops early.

### Step 6 — Logging (Module 6)
Every run is appended to `logs/pipeline.jsonl` with the full input, both playlists, all scores, issues, feedback, and iteration count. Human feedback (optional star ratings) is stored separately in `logs/human_feedback.jsonl`.

---

## 4. Data

The catalog has **48 songs** stored in `data/songs.csv`. Each song has: id, title, artist, genre, mood, energy (0–1), tempo in BPM, valence, danceability, and acousticness.

**Genre distribution (selected):**
- lofi: 14 songs
- rock: 11 songs (expanded from 1 in v1.0 to support the deep_rock profile)
- ambient: 5 songs
- jazz: 3 songs
- Other genres (1–2 each): pop, synthwave, hip-hop, classical, electronic, soul, indie rock, reggae, country, experimental, indie pop

**Mood distribution (selected):**
- chill: 11 songs
- focused: 7 songs
- intense / aggressive / energetic: 11 songs combined
- Other moods (1–3 each): happy, relaxed, melancholic, moody, romantic, peaceful, dreamy, nostalgic

**Changes from v1.0:**
- Original catalog had 18 songs. Expanded to 48 by adding 20 lofi/ambient/jazz songs and 10 high-energy rock songs.
- The rock expansion was necessary after testing revealed the refiner produced completely off-genre results when only 1 rock song existed in the catalog.

**What's still missing:**
- Genres with zero representation: metal, R&B, Latin, K-pop, country rock, blues
- Moods like *angry*, *uplifting*, *nostalgic* are sparse
- No song lyrics, release year, or popularity signals
- No real user listening history

---

## 5. Strengths

**Self-correction works.** When the initial playlist contains off-genre or off-mood songs, the refinement loop reliably replaces them. The deep_rock profile went from a 5.33 reliability score (initial playlist included indie pop and hip-hop) to 8.3+ after one refinement iteration once the catalog had sufficient rock songs.

**Dual evaluation catches different failure modes.** The heuristic evaluator catches structural problems (too many songs from one artist, low genre diversity). The LLM critic catches semantic problems (songs that are technically diverse but tonally incompatible). Neither alone is sufficient — a maximally diverse but off-genre playlist scored 9.84 heuristically but 1.0 from the LLM.

**Graceful degradation.** If the Gemini API is unavailable (quota exceeded, network error, invalid key), the pipeline continues with heuristic-only scoring instead of crashing. The fallback is logged and visible in the output.

**Transparent scoring.** Every recommendation includes the specific features that contributed to its score. Every evaluation includes the exact issues flagged. The system never makes a decision without leaving an auditable trail.

**Works well for well-represented profiles.** Chill lofi, sad/hopeful, and romantic evening profiles all produce playlists with reliability scores above 8.0 without requiring refinement.

---

## 6. Limitations and Bias

**Genre gatekeeping (inherited from v1.0, partially mitigated):**
The genre match bonus (+2.0) is still the single largest scoring factor — 40% of the non-embedding score. A song in an adjacent genre (indie rock vs rock, indie pop vs pop) scores 0 on genre even if it sounds identical. This was identified in v1.0 and remains in v2.0 as a known limitation. The LLM critic now partially compensates by flagging genre mismatch issues, which trigger the refiner to use a mood-family-aware filter instead of strict genre matching.

**Small catalog limits refinement quality:**
Even at 48 songs, some genre/mood combinations have very few candidates. A user requesting *romantic R&B* or *angry metal* will find no genre matches at all. The refiner cannot produce a good playlist from nothing — it can only rerank what exists.

**Mood family mapping is hand-coded:**
The refiner uses a hardcoded dictionary of compatible moods (e.g., "intense" accepts {intense, aggressive, energetic, moody}). This is a reasonable approximation but will fail for moods not in the map, defaulting to exact match only.

**LLM scores reflect training data bias:**
Gemini evaluates playlists through the lens of its training data, which is predominantly Western, English-language music culture. A playlist of traditional instruments or regional genres may be scored lower due to unfamiliarity, not actual quality.

**50/50 weighting is not empirically tuned:**
The equal blend of heuristic and LLM scores was chosen as a reasonable default. It has not been calibrated against real user satisfaction data. Human feedback is now being collected via `--feedback` for future retuning.

**Refinement can loop without improvement:**
If both iterations produce poor playlists (because the catalog has no good alternatives), the pipeline terminates with a low reliability score rather than escalating or explaining why it could not improve. A future version should detect this and surface a clearer message.

---

## 7. Evaluation

### Automated testing
23 unit tests cover all modules independently. The LLM is mocked in tests so they run offline and deterministically. All 23 pass.

```
python -m pytest tests/test_pipeline.py -v
```

### Live profile testing (5 profiles)

| Profile | Initial Reliability | Final Reliability | Iterations |
|---|---|---|---|
| chill_lofi | 8.30 | 8.30 | 0 |
| sad_hopeful | 8.05 | 8.05 | 0 |
| romantic_evening | 7.90 | 7.90 | 0 |
| high_energy_workout | 7.60 | 8.10 | 1 |
| deep_rock | 5.33 | 8.30 | 1 |

Profiles with well-represented genres in the catalog (lofi, ambient) pass on the first attempt. Profiles that initially mix off-genre songs (deep_rock, workout) trigger refinement and improve.

### Key evaluation finding
A refined playlist once scored 9.84/10 heuristically but 1.0/10 from the LLM. The heuristic rewarded its perfect genre diversity (every song from a different genre), while the LLM correctly identified that the genres were entirely wrong for the query. This confirmed that both evaluators are necessary — the heuristic alone can be gamed by structural correctness without semantic relevance.

---

## 8. Future Work

**1. Partial genre credit.**
Related genres (indie pop / pop, indie rock / rock) should earn partial credit (+1.5) instead of zero. This would reduce the filter bubble without removing genre as a signal. This was identified in v1.0 and remains the highest-priority scoring improvement.

**2. Expand the catalog to 200+ songs.**
The refinement loop is only as good as the catalog it draws from. With 48 songs, several genre/mood combinations have 1–2 representatives. A larger catalog would make the refiner meaningfully more powerful, particularly for rock, R&B, and metal profiles.

**3. Calibrate the 50/50 score weighting using human feedback.**
Human feedback is now being collected via `--feedback`. Once enough ratings are gathered, a simple regression could determine whether heuristic or LLM scores better predict user satisfaction — and adjust the blend accordingly.

**4. Steepen the energy penalty at the extremes.**
Using a squared gap `(1 - gap²) × 2` instead of a linear gap would punish large energy mismatches more aggressively, improving results for extreme energy profiles (workout, ambient sleep).

**5. Add a "no good candidates" warning.**
When the refiner cannot find enough genre/mood-matching songs in the catalog, it should surface an explicit message instead of silently returning a low-quality playlist with a poor reliability score.

**6. Connect to a real music API.**
Replace the static CSV with a Spotify or MusicBrainz integration so the catalog scales to millions of songs and recommendations are based on real audio features.

---

## 9. Personal Reflection

**What the self-critique loop taught me:**
Building AudioVerse 1.0 showed me that scoring formulas produce explainable results. Building AudioVerse 2.0 showed me that explainability is not the same as correctness. A system can explain every point in its score and still recommend the wrong thing, because the formula itself has gaps the numbers cannot capture. Adding the LLM critic was not about making the system smarter — it was about adding a different *kind* of judgment that the heuristics structurally cannot provide.

**The most surprising failure:**
The 9.84/10 heuristic score for a completely wrong playlist was genuinely surprising. The refiner had replaced lofi songs with reggae, classical, and country. Each song was from a unique artist and genre — perfect structural diversity. The heuristic had no way to know that none of those genres were what the user asked for. That single failure made the dual-evaluation design feel necessary rather than optional.

**What changed from v1.0:**
In v1.0 the biggest lesson was that genre weight dominates everything. In v2.0 the biggest lesson was that individual metrics can all be correct while collectively missing the point. Diversity is good. Novelty is good. Genre spread is good. But a playlist can maximize all three and still be wrong. The only way to catch that is with a signal that understands the *meaning* of the request — which is exactly what the LLM critic provides.

**On AI collaboration:**
This project was built collaboratively with an AI assistant. The human feedback module was a suggestion I had not planned — it added a real evaluation dimension beyond automated metrics. The initial JSON parsing approach was a flaw that only surfaced in production when Gemini returned trailing commas that Python's `json` module could not parse. Both experiences reinforced the same lesson: AI suggestions are a starting point, not a final answer. The real work is testing them against reality.
