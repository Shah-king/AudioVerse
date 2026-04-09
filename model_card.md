# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

Give your model a short, descriptive name.  
Example: **VibeFinder 1.0**  

---

## 2. Intended Use  

Describe what your recommender is designed to do and who it is for. 

Prompts:  

- What kind of recommendations does it generate  
- What assumptions does it make about the user  
- Is this for real users or classroom exploration  

---

## 3. How the Model Works  

Explain your scoring approach in simple language.  

Prompts:  

- What features of each song are used (genre, energy, mood, etc.)  
- What user preferences are considered  
- How does the model turn those into a score  
- What changes did you make from the starter logic  

Avoid code here. Pretend you are explaining the idea to a friend who does not program.

---

## 4. Data  

Describe the dataset the model uses.  

Prompts:  

- How many songs are in the catalog  
- What genres or moods are represented  
- Did you add or remove data  
- Are there parts of musical taste missing in the dataset  

---

## 5. Strengths  

Where does your system seem to work well  

Prompts:  

- User types for which it gives reasonable results  
- Any patterns you think your scoring captures correctly  
- Cases where the recommendations matched your intuition  

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

---

## 9. Personal Reflection  

A few sentences about your experience.  

Prompts:  

- What you learned about recommender systems  
- Something unexpected or interesting you discovered  
- How this changed the way you think about music recommendation apps  
