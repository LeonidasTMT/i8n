# QC & lessons learned (JP → EN)

The checklists to run, and the mistakes actually made on this project so they
don't repeat. "Look out for" items are general JP→EN traps.

> Meta-level QC first: **faithful translation** — the author's script is ground
> truth; no silent edits, no register changes to names/terms, line structure
> preserved. Full doctrine: [../TRANSLATION.md](../TRANSLATION.md). The checks below
> catch the mechanical drift that doctrine prevents.

## Per-file QC checklist (run before shipping)

- [ ] **Byte/line diff vs the original:** only intended lines changed; zero
      line-count drift (no accidental added/removed lines).
- [ ] **Only-additions proof:** files you did *not* touch are byte-identical to
      your previous known-good patch. (Stronger than any string-presence check.)
- [ ] **Every entry decodes as CP932** in the built archive.
- [ ] **No JP leftovers** on the player-visible strings you targeted (scan target
      literals for non-ASCII; e.g. a fully-translated ribbon → 0 non-ASCII).
- [ ] **Functional syntax preserved:** hotkeys `(&S)` unique & consistent, tabs
      `\t`, file filters `(*.bmp)|*.bmp`, KAG tags `[r]/[e1]/[e2]`, `[link]`,
      format placeholders (`%s`, `{0}`).
- [ ] **Width budget respected:** no rendered story line exceeds the half-width
      cap; speaker labels still on their own line.
- [ ] **Re-extract what you built** and verify from disk after copying to the
      game dir (not just the build output).

## Build/verification discipline

- [ ] **Idempotent re-flow:** source from a clean pre-reflow backup, apply
      editorial fixes *before* wrapping. Never re-wrap already-wrapped text.
- [ ] **NO-MATCH safety net** on every string-replacement pass (abort on miss).
- [ ] **One named backup per stage** before each repack (`..._before_ks.xp3`,
      `..._before_tjs.xp3`). Cheap, and it's your rollback + diff baseline.
- [ ] **Assert counts** you expect (e.g. exactly 14 story files; entry set ==
      expected names) so a silent drop is caught.

## Lessons learned (things that cost time here)

1. **Encoding is the whole game.** KiriKiri text is CP932, not UTF-8, and the
   terminal mangles it. I misread codepoints by eye (thought U+623B `戻` was `も`,
   U+308A `ら` was `ど`) and only got clean matches after dumping exact codepoints
   and using `\u` escapes. *Never eyeball CJK in a shell; dump codepoints.*

2. **Match the full quoted literal, with a safety net.** Replacing fragments can
   hit unintended spots. Match `"…"` whole, assert `count>0`, and confirm the count
   is what you expect when a string legitimately repeats (Yes/No appear once each).

3. **Scope discipline saves features.** Engine files mix player-facing text with
   error/debug/internal strings. I translated only the former (ribbon, save/load
   prompts, confirms) and left debug/error text in Japanese. Over-translating risks
   breaking internal logic and wastes effort. When unsure, leave it and note why.

4. **Functional syntax is not decoration.** File-dialog filter specs
   (`(*.bmp)|*.bmp`), menu hotkeys, tabs, and KAG tags are *parsed*, not shown.
   I kept `(*.bmp)|*.bmp` / `(*.kdt)|*.kdt` and every `(&X)` byte-exact while
   translating only the human words around them.

5. **Verify by round-trip + only-additions, not by eye.** The decisive check was:
   re-extract the built archive and assert the untouched 14 `.txt` + 6 `.ks` are
   byte-identical to the previously-shipped patch. That proved "I only added the 4
   `.tjs`" in one line. Ad-hoc string-presence checks are weak (see mistake #2).

6. **Half-width budget drives wrapping.** JP counts half-width units (kanji = 2);
   English must wrap to the same cap so it fits the original box. Measure the
   rstrip'd raw width for the wrap trigger; assert prose segments ≤ cap while
   *skipping* bracket/special-syntax lines when checking.

7. **Bracket/punctuation normalization is a judgment call — document it.** I turned
   decorative CJK corner brackets `「」` into ASCII `[ ]` in save/load prompts
   (English readers don't expect them) but left functional parts alone. Any such
   decision should be a conscious, noted choice, not an accident.

8. **Longer English than Japanese → UI overflow.** Ribbon/menu labels grow; expect
   Windows overflow arrows on narrow windows. It's cosmetic and menus stay usable,
   but shorten top-level labels (e.g. "Return to Title" → "Title") if it clips.
   Flag this to the user rather than silently shipping a clipped ribbon.

9. **Don't vendor engine source into a workflow repo.** The C++ trees
   (`krkr2`/`krkrz`) are third-party GPL and huge. Reference them by pointer for
   internals (e.g. `XP3Archive.cpp`); keep the i8n repo to small tools + docs.

10. **Story fidelity is its own QC pass.** Speaker labels/attribution, character
    names staying consistent, voice, and ellipsis convention each need a dedicated
    read-through — separate from the byte-level checks above. (This project had a
    full story-QC pass plus later targeted fixes: "Onlookers", "nodded", "It's
    coming out", "coming at me"→"coming out".)

## Mistakes actually made (and the fix that stuck)

- **Misread codepoints by eye** → fixed by dumping exact codepoints + `\u` escapes.
  Rule: dump, don't guess; re-dump if a dump is truncated in the terminal.
- **Over-strict spot-check gave a false alarm** (looked for "Onlookers" in the
  wrong scene). The byte-identical-to-prior-patch check was the real proof. Rule:
  verify against the known-good prior build, not ad-hoc string presence.
- **Truncated codepoint dump** on a long line → re-dumped the full line before
  finalizing that replacement.

## General JP→EN "look out for" traps

- **Fullwidth vs halfwidth punctuation:** `？！。、－（）」』` vs their ASCII
  forms. Get the codepoints exact (see [ENCODING.md](ENCODING.md)).
- **Hotkey letters** in menus must stay unique and consistent across items.
- **Ellipsis convention:** JP `…` (single) vs EN `...`. Pick one and be consistent.
- **Speaker/name consistency:** same character = same English name throughout;
  keep "Me"/"Girl"-style speaker labels intact on their own line.
- **Placeholders/format strings:** never translate `%s`, `{0}`, `\t`, tags, or
  numeric/ID tokens.
- **Width budgets:** keep lines within the engine's text box or it clips/wraps
  badly; re-flow after translation, not before.
- **Don't translate what isn't shown:** error/debug/internal strings stay as-is
  unless the user asks.
