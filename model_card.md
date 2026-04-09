# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

Give your model a short, descriptive name.  
Example: **VibeFinder 1.0**  

**VibeMatch 1.0** — a point-based music recommender that scores songs against a listener's taste profile and returns the top matches.

---

## 2. Intended Use  

Describe what your recommender is designed to do and who it is for. 

Prompts:  

- What kind of recommendations does it generate  
- What assumptions does it make about the user  
- Is this for real users or classroom exploration  

VibeMatch generates top-5 song recommendations based on a user's stated genre, mood, and energy preferences. It assumes the user already knows what they like and can express it as a profile. It is built for classroom exploration — not a production app. It should not be used as a substitute for a real music platform like Spotify, and it will not work well for users who want to discover music outside their stated taste, since the scoring actively favors songs that match the user's preferences exactly.

**Intended use:** Learning how content-based filtering works, testing scoring formulas, classroom demos.  
**Not intended for:** Real music discovery, users with niche or cross-genre tastes, catalogs larger than a few dozen songs.

---

## 3. How the Model Works  

Explain your scoring approach in simple language.  

Prompts:  

- What features of each song are used (genre, energy, mood, etc.)  
- What user preferences are considered  
- How does the model turn those into a score  
- What changes did you make from the starter logic  

Avoid code here. Pretend you are explaining the idea to a friend who does not program.

Every song in the catalog gets a score out of 6.0 based on how well it matches what the user wants. Here is what goes into the score:

- **Genre** — if the song's genre exactly matches the user's preference, it earns +2.0 points. This is the biggest factor.
- **Mood** — if the song's mood matches, it earns +1.0 point.
- **Energy** — the closer the song's energy level is to the user's target (on a 0 to 1 scale), the more points it earns, up to +2.0. A perfect energy match gives the full 2.0.
- **Danceability bonus** — if the song's danceability is close to what the user prefers, it earns +0.5.
- **Tempo bonus** — if the song's BPM falls inside a range the user set, it earns +0.5.

All 18 songs are scored, then sorted from highest to lowest. The top 5 are returned along with a plain-English explanation of which features contributed to each score.

---

## 4. Data  

Describe the dataset the model uses.  

Prompts:  

- How many songs are in the catalog  
- What genres or moods are represented  
- Did you add or remove data  
- Are there parts of musical taste missing in the dataset  

The catalog has **18 songs** stored in `data/songs.csv`. Each song has: title, artist, genre, mood, energy (0–1 scale), tempo in BPM, valence, danceability, and acousticness.

**Genres:** pop, lofi, rock, ambient, jazz, synthwave, indie pop, hip-hop, classical, electronic, soul, indie rock, reggae, country, experimental — 15 genres total, most with only 1 song. Lofi is the exception with 3.

**Moods:** happy, chill, intense, focused, relaxed, moody, aggressive, nostalgic, energetic, romantic, melancholic, dreamy — 12 moods total.

No songs were added or removed. The dataset was used as-is.

**What's missing:** Moods like *sad*, *angry*, *peaceful*, and *uplifting* don't exist in the catalog. Genres like *metal*, *country rock*, and *R&B* have no representation. Users who prefer these will never get a genre or mood bonus — the system silently ignores those preferences.

---

## 5. Strengths  

Where does your system seem to work well  

Prompts:  

- User types for which it gives reasonable results  
- Any patterns you think your scoring captures correctly  
- Cases where the recommendations matched your intuition  

The system works best when the user's genre and mood are both present in the catalog.

- **Chill Lofi** was the strongest result — Library Rain scored a perfect 6.0/6.0 because every feature aligned: genre, mood, energy, danceability, and tempo all matched.
- **Deep Intense Rock** also gave a strong #1 (Storm Runner at 5.98/6.0) because the genre and mood both existed in the dataset.
- The score explanation is easy to read and clearly shows why each song was picked, which makes the output feel trustworthy.
- The energy similarity formula works well as a ranking layer within genre groups — small energy differences produce small score differences, which feels proportional.

---

## 6. Limitations and Bias 

Where the system struggles or behaves unfairly. 

Prompts:  

- Features it does not consider  
- Genres or moods that are underrepresented  
- Cases where the system overfits to one preference  
- Ways the scoring might unintentionally favor some users  

**Discovered weakness — Genre gatekeeping creates a filter bubble:**
The most significant weakness discovered during experimentation is that the genre match carries so much weight (+2.0 out of a maximum 5.0 points, or 40% of the total score) that it effectively locks users inside a single-genre bubble. During testing, the "Rooftop Lights" song — which is labeled *indie pop* rather than *pop* — was penalized the full 2.0 points compared to "Gym Hero," a pop song whose mood (*intense*) completely contradicts what a happy, high-energy pop user actually wants; yet Gym Hero still ranked higher purely because of the genre label. This means the system can recommend a song that *feels* wrong while ignoring one that *sounds* right, just because of a one-word label difference. The problem is compounded by the fact that the dataset contains only one or two songs per genre for most categories, so a user whose preferred genre is underrepresented (such as *metal* or *ambient*) immediately loses access to the genre bonus for every single song and receives recommendations driven almost entirely by energy similarity alone — a much weaker signal. A fairer design would award partial credit for related genres (for example, *indie pop* scoring 1.5 instead of 0 against a *pop* preference), which would reduce the filter bubble without removing genre as a useful feature.

---

## 7. Evaluation  

How you checked whether the recommender behaved as expected. 

Prompts:  

- Which user profiles you tested  
- What you looked for in the recommendations  
- What surprised you  
- Any simple tests or comparisons you ran  

No need for numeric metrics unless you created some.

I tested the first three profiles — High-Energy Pop, Chill Lofi, and Deep Intense Rock — by running the recommender and checking whether the top-5 results matched what I would intuitively expect for each listener type. For High-Energy Pop, I looked at whether the top song matched on both genre and mood, and whether the score gap between #1 and #2 was meaningful. What I found was that mood acted as a decisive tiebreaker within the same genre: Sunrise City (pop, happy) ranked above Gym Hero (pop, intense) by exactly 1.0 point — the mood bonus — even though Gym Hero had a slightly closer energy match. To confirm this, I temporarily disabled the mood check entirely and observed that Gym Hero immediately jumped to #1, while Sunrise City fell to #2. This experiment revealed that mood is a critical factor specifically when two songs share the same genre, since the genre bonus already equalizes their base scores and mood becomes the only meaningful differentiator. However, mood alone could not overcome a genre mismatch — Rooftop Lights, which correctly matched the happy mood, still ranked far below both pop songs because it lost the full 2.0-point genre bonus.

---

## 8. Future Work  

Ideas for how you would improve the model next.  

Prompts:  

- Additional features or preferences  
- Better ways to explain recommendations  
- Improving diversity among the top results  
- Handling more complex user tastes  

**1. Partial genre credit.**
Related genres like *indie pop* and *pop* or *indie rock* and *rock* are musically very similar but currently score the same as completely unrelated genres. Giving partial credit (e.g., +1.5 for a close genre instead of +2.0 or 0) would reduce the filter bubble and let good songs from adjacent genres surface.

**2. Warn the user when a preference goes unmatched.**
If the user's mood doesn't exist in the catalog, or their genre has zero songs, the system should say so clearly. Right now it silently returns results that feel off with no explanation. A simple line like "Note: no songs matched your mood preference" would make the output honest.

**3. Steepen the energy penalty at the extremes.**
A user wanting energy 0.0 still sees high-energy songs because the linear penalty is too gentle. Using a squared gap — `(1 - gap²) × 2` instead of `(1 - gap) × 2` — would punish large energy mismatches much more heavily and make the recommendations feel right for low-energy or high-energy users.

---

## 9. Personal Reflection  

A few sentences about your experience.  

Prompts:  

- What you learned about recommender systems  
- Something unexpected or interesting you discovered  
- How this changed the way you think about music recommendation apps  

**Biggest learning moment:**
I expected genre to matter, but not *this much*. Seeing Gym Hero (wrong mood, same genre) beat Rooftop Lights (right mood, wrong genre label) made it clear that a single weight choice can quietly dominate an entire system. The number 2.0 looks harmless until you realize it's 40% of the max score and nothing else can reliably overcome it.

**How AI tools helped, and when I double-checked:**
AI helped me quickly spot patterns across all 9 profiles at once and interpret score differences. But I still needed to verify the math by hand — for example, confirming that `(1 - |0.9 - 0.82|) × 2 = 1.84` actually matched the code output. AI explains patterns confidently even when the numbers are slightly off, so checking the raw terminal output against the formula directly was important.

**What surprised me about simple algorithms:**
The recommendations *feel* real even though the logic is just addition. When Library Rain scored 6.0/6.0 for a Chill Lofi user, it genuinely seemed like the right pick. We don't need a neural network to produce a result that feels correct. Simple recommendation can do the job with the right features and reasonable weights.

**What I'd try next:**
I'd expand the catalog to at least 100 songs so each genre has several representatives. With only 18 songs, one missing genre breaks the entire experience for that user type. I'd also add a diversity mode that forces the top-5 to include at least 3 different genres, so users occasionally discover something outside their usual taste instead of seeing the same genre repeated back five times.
