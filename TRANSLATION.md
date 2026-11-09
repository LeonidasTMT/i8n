# Translation doctrine (applies to every engine)

Faithful localization is the whole job. These principles outrank any
engine-specific note in this repo and apply to translating *any* script —
KiriKiri, Ren'Py, Tyrano, MML, Unity/Mono, whatever. When an engine doc and this
file disagree, this file wins: **faithful transfer beats "better" writing.**

## 0. The rule that outranks everything else

**The author's original script is ground truth.** Your job is to translate it
faithfully; it is *not* your job to edit for the author. If something in the
source looks like a mistake, awkward, or badly paced, assume it is intentional
until proven otherwise — and even then, **flag it**, don't silently change it.

## 1. Don't assume source mistakes

- Suspected typos, odd spacing (double spaces), missing/extra punctuation,
  unusual capitalization, repeated words — often deliberate (voice, emphasis,
  pacing). Preserve meaning-bearing quirks; don't normalize them away.
- If you can't tell intent from error: note it in a changelog/note. Never
  silently "fix" source text.

## 2. You are not the editor

- Don't tighten prose, reword for clarity, deduplicate, or "make it flow."
  Equivalence to the source is the goal; enhancement is out of scope.
- **Pacing is craft.** Line length, where lines break, run-on vs. choppy
  phrasing — all part of the author's intent. A short line stays short; a long
  one stays long. Don't re-flow or re-break lines to look nicer.

## 3. Names / terms / labels: match register, don't embellish

- Translate the *meaning*, not the *register*. Do **not** add articles ("The"),
  possessives, honorifics, or capitalization the source lacks.
- Example: a bare label 「観客」 → **"Onlookers"**, not *"The Onlookers"* — it's
  unlikely to be a formal title, so don't promote it to one.
- If the source uses a bare noun, use a bare noun. If it's a full formal title,
  render it as a title.

## 4. Consistency over cleverness

- Same source term → same translation, every occurrence. Keep a glossary; never
  vary a name/term for "variety."
- Per-character voice: preserve the *relative* register differences between
  speakers even when one reads oddly in isolation.

## 5. Preserve structure and markers

- Speaker labels, brackets, special syntax, line breaks, spacing — author intent.
  Translate text *within* the structure; don't restructure or rewrap beyond what
  the engine/encoding strictly requires (and if you must, say why).

## 6. Literal first, then check

- When unsure between interpreting and literalizing, default to the more
  faithful/literal reading and flag uncertainty. Don't force-resolve ambiguity
  the author left open — a faithful translation may stay ambiguous.

## 7. Hold conventions steady

- Numbers, dates, units, honorifics, punctuation: pick one convention per project
  and keep it. Don't modernize or over-localize beyond the stated target.

## Anti-patterns (the mistakes this doctrine prevents)

- "The Onlookers" instead of "Onlookers" — adding register/article the source
  lacks.
- Re-flowing/re-wrapping lines to look nicer when the original line breaks carry
  pacing intent.
- Silently fixing a suspected source typo instead of flagging it.
- Varying a repeated line/term for variety when the author repeats deliberately.
- Rewriting awkward prose because it's awkward.

## When you disagree with the source

Render it faithfully; don't be righter than the author. If a choice feels wrong,
note it — don't override the author silently.
