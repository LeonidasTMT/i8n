# Translation doctrine (applies to every engine)

Faithful localization is the whole job. These principles outrank any
engine-specific note in this repo and apply to translating *any* script —
KiriKiri, Ren'Py, Tyrano, MML, Unity/Mono, whatever. When an engine doc and this
file disagree, this file wins: **faithful transfer beats "better" writing.**

## The rule that outranks everything else

**The author's original script is ground truth.** Your job is to translate it
faithfully; it is *not* your job to edit for the author. If something in the
source looks like a mistake, awkward, or badly paced, assume it is intentional
until proven otherwise — and even then, **flag it**, don't silently change it.

## Before you translate: character pass

- Do a **high-level read-through of the whole script first**, before translating
  line-by-line. Understand each character before you render their voice.
- Build an **internal character doc** (a "character bible") per project: how each
  speaks — formality level, word choices, tone, rhythm — and any **quirks or
  catchphrases**.
- Decide in advance **how each quirk maps to English.**
- **Only render a quirk if it actually appears in the source JP.** You are
  documenting and carrying over what's there, not inventing voice. If a character
  has no quirk in the source, don't add one; if they have several, carry all of
  them where they occur.

## Don't assume source mistakes

- Suspected typos, odd spacing (double spaces), missing/extra punctuation,
  unusual capitalization, repeated words — often deliberate (voice, emphasis,
  pacing). Preserve meaning-bearing quirks; don't normalize them away.
- If you can't tell intent from error: note it in a changelog/note. Never
  silently "fix" source text.

## You are not the editor

- Don't tighten prose, reword for clarity, deduplicate, or "make it flow."
  Equivalence to the source is the goal; enhancement is out of scope.
- **Pacing is craft.** Line length, where lines break, run-on vs. choppy
  phrasing — all part of the author's intent. A short line stays short; a long
  one stays long. Don't re-flow or re-break lines to look nicer.

## Names / terms / labels: match register, don't embellish

- Translate the *meaning*, not the *register*. Do **not** add articles ("The"),
  possessives, honorifics, or capitalization the source lacks.
- Example: a bare label 「観客」 → **"Onlookers"**, not *"The Onlookers"* — it's
  unlikely to be a formal title, so don't promote it to one.
- If the source uses a bare noun, use a bare noun. If it's a full formal title,
  render it as a title.

## Consistency over cleverness

- Same source term → same translation, every occurrence. Keep a glossary; never
  vary a name/term for "variety."
- Per-character voice: preserve the *relative* register differences between
  speakers even when one reads oddly in isolation (see the character pass).

## Ambiguity: resolve structural, preserve intentional

- Japanese structure (pro-drop, topic-comment order, omitted subjects) often makes
  a line ambiguous **by construction**. If the next line / surrounding context
  makes it clear, you **may** resolve it for clarity — that's faithful, because
  you're surfacing what the source already implies, not changing its meaning.
- Do **not** resolve **intentional** ambiguity: deliberate cutoffs (trailing off),
  censored/redacted text (`■■■`, `▓▓`), ellipses-as-silence, withheld words.
  Preserve those exactly — they're an authorial device, not a gap to fill.
- The test: is the ambiguity **Japanese economy** (safe to resolve from context) or
  an **authorial device** (preserve)? Cutoffs, censor blocks, silence → leave them.

## Pronouns & references (the "you're" vs "it's" problem)

- Japanese drops pronouns and leans on context; English forces you to name the
  referent. This is where silent errors hide — a wrong pronoun changes who/what
  the line is about.
- Determine the antecedent from **context**: surrounding lines, who is speaking,
  what was just mentioned, and scene logic. Don't guess.
- Watch the **"you" trap**: a line that *reads* like it's addressing "you" is often
  actually about *it / he / she*, or an inanimate/abstract thing. Real case: a line I
  rendered as *"you're coming out"* was actually 射精 (`detchau`, ejaculation) — i.e.,
  **"it's coming out"** (semen), not a person. The surrounding scene made it
  unambiguous; the error came from translating the line in isolation.
- If the reference stays genuinely undecidable, prefer the reading consistent with
  scene logic and flag it; keep it as neutral/correct as possible.
- Record resolved references in the character doc so they stay **consistent**
  across the script (same antecedent → same pronoun every time).

## Preserve structure and markers

- Speaker labels, brackets, special syntax, line breaks, spacing — author intent.
  Translate text *within* the structure; don't restructure or rewrap beyond what
  the engine/encoding strictly requires (and if you must, say why).

## Hold conventions steady (incl. honorifics)

- Numbers, dates, units, punctuation: pick one convention per project and keep it.
  Don't modernize or over-localize beyond the stated target.
- **Honorifics:** keep `-san` / `-kun` / `-chan` / `-sama` / `-senpai` romanized; do
  **not** localize them to English titles (Mr./Ms./Sir/Ma'am). Keep the same
  honorific for the same person throughout — and if it *changes* in-source, that's
  meaningful (a relationship shift), so preserve the change.

## Anti-patterns (the mistakes this doctrine prevents)

- "The Onlookers" instead of "Onlookers" — adding register/article the source lacks.
- "You're coming out" when the source has no human subject — it's "it's coming out."
- Inventing a character quirk/catchphrase that isn't in the source.
- Localizing -san/-chan to Mr./Sir instead of keeping the honorific.
- Re-flowing/re-wrapping lines to look nicer when the original breaks carry pacing intent.
- Silently fixing a suspected typo; varying a repeated term for variety; rewriting awkward prose.
- "Clarifying" an intentional cutoff/censor by filling in the withheld word.

## When you disagree with the source

Render it faithfully; don't be righter than the author. If a choice feels wrong,
note it — don't override the author silently.
