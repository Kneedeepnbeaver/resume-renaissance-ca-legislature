## California Legislature Writing Guidelines (1990s) – Historical Notes

This app’s prompts are grounded in a short set of writing rules that were originally given to the creator of this app in the 4th grade.

They’re simple, practical rules for how to write to legislators and public offices: clear, respectful, concrete, and concise. The app adapts these rules for **modern job applications to legislative offices**.

Below is the distilled version used inside the prompts. It’s intended as **public, reusable guidance**, not legal advice.

---

### CA Legislature Writing Guidelines (adapted for job applications)

- **Be brief**: Get to the point quickly.  
  Cover letters: one page max. Effectiveness is often inversely proportional to length.

- **Introduce yourself simply**:  
  Tell who you are without making a biography. A simple statement of role/affiliation suffices.

- **Be specific**:  
  Match concrete job requirements. Use concrete examples and outcomes, not vague claims.

- **Make it personal**:  
  Use your own words. Avoid generic templates. Tailor each application.

- **Give your reasons**:  
  State your case clearly. Explain why you're a fit and what value you bring.

- **Be constructive**:  
  Focus on what you can contribute. Emphasize solutions and contributions.

- **Be courteous and reasonable**:  
  Maintain a professional tone throughout. Never threaten or be rude.

- **Don't be vague**:  
  Use concrete outcomes, metrics, and examples.

- **Don't apologize**:  
  Don't apologize for taking their time or use weak openings.

- **Don't overstate**:  
  Give reasons but don't overstate. Credibility matters.

---

### How the app uses these rules

The core prompts in `app/generation/prompts.py` embed these guidelines into the **system message** for both:

- The **resume generator** (ATS‑friendly, concise, focused on relevant experience), and  
- The **cover letter generator** (brief, specific, courteous, one page max).

In practice, this means:

- Resumes and cover letters are biased toward **short, focused, concrete** writing.  
- The model is discouraged from:
  - Long, flowery introductions
  - Vague claims without examples
  - Overblown “I am the perfect candidate” language
- The outputs try to read like something **a legislative office would actually want to read**—not generic corporate boilerplate.

Because these rules are short and conceptual, they can be safely reused and adapted in other projects, as long as they’re treated as historical writing guidance rather than current official policy.

