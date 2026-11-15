# Unity (Mono): JP→EN workflow (extract → translate → native re-bake → QC → verify)

Proven end-to-end on a full JP→EN **native build** of a commercial Mono Unity game
(≈2,800 asset string fields + scenario TextAsset CSVs + managed DLL `#US` strings).
No runtime mod in the shipped build — the game's own files hold the English.
The invariant throughout: **only the bytes you intended change, and you can prove it.**

> Scope: Mono builds (managed C# assemblies on disk). IL2CPP strips the assemblies
> to native code — a different, harder case not covered here.

## 0. Working-copy discipline (before touching anything)

- Copy the whole game directory to a working build (`<game>_en`); **originals and
  any `_bkp` stay untouched**. All patches land in the working copy.
- Before every patch: a timestamped backup dir holding the pre-patch bytes of each
  file you're about to change, plus a named backup of the canonical table
  (`pairs.txt.bak_<tag>`). One per stage; cheap; they are your rollback + diff baseline.
- Never trust a build you didn't re-read after copying: verify from disk.

## 1. Extract & inventory

Three containers hold player-visible text (see `FORMAT.md`):

- **Asset string fields** (`levelN.assets`, `sharedassetsN.assets`, …): dump every
  string field with its path → key `<file>#<field.path>`. Assert the **id set is
  identical** between JP and EN builds — same fields, only values differ.
- **Scenario TextAssets**: scenario dialogue is **not loose files** — it's CSV
  `TextAsset` blobs packed inside `resources.assets`, addressable by pathId.
  "Five scenario CSVs" = five TextAsset blobs, not five physical files. Each CSV's
  `message` column is the exact runtime `.text` string; `lineId` order = playback
  order. Extract verbatim to working CSVs.
- **Managed DLL `#US` heap** (`<Game>_Data/Managed/*.dll`): dump (offset → literal)
  per assembly. Key `us:<hash>`.

Gotchas found the hard way:

- `udr.json` maps to `Resources\unity default resources`, not a top-level file —
  follow the JSON, not the filename.
- **Provenance first:** reverse-search a known in-game string against the
  containers to confirm which one actually holds it before editing anything.

## 2. Triage: display vs ID/key reference (the black-screen lesson)

Not every JP-containing field is display text. Serialized assets also carry
**story/event/asset ID + key reference fields** — identifiers the engine matches
against its scenario tables. EN-ifying an ID field breaks scene loading; the
symptom is a **black screen on that scene**.

- Before any bulk inject, classify every diff pattern **KEEP_EN** (display) vs
  **REVERT_JP** (ID/key reference).
- Classify by **decompiled call-site context**, not heuristics: read what the
  field is compared/looked-up against.
- Real case: a bulk pass EN-ified 1,179 ID/key fields → one H-scene went black;
  fixed by reverting exactly those fields to pristine JP (display fields kept EN),
  verified clean, user playtest green.

Also classify: player-visible vs internal/log/debug (leave the latter unless asked)
and baked-image labels (paint, not text — separate art track).

## 3. Translate + canonical table

- Doctrine: `../TRANSLATION.md` (faithful transfer; character pass; POV discipline;
  verb-form continuity; honorifics; structure intact).
- **One source of truth**: `pairs.txt` — one line per key, `JP literal=EN value`,
  UTF-8 no BOM. Everything else (inject files, QC datasets) is derived from it.
- **Line-ending discipline:** record the table's line-ending style before editing
  (CRLF in this project). A default LF rewrite silently converts every separator.
  Re-diff vs the backup after writing: changed-line count must equal the intended
  edit count exactly.
- **Corpus binding law:** one source line → exactly ONE EN value, byte-identical in
  every container/scenario it appears in. Recurring keys need explicit bindings,
  else batch-promote order silently picks a winner.

## 4. Native re-bake (inject)

Per string class, write EN into the source container and ship the replaced file:

- **Asset fields**: extractor's inject mode — byte-exact replacement of targeted
  values only; non-target strings must come back byte-identical. Verify: id set
  identical + full re-extract diff = intended changes only.
- **Scenario TextAssets**: scenario-bytes inject — replace the whole CSV blob bytes
  at its blob index inside `resources.assets`. Rebuild each CSV structure-preserving
  (all columns, line breaks intact); verify 0 JP remaining in player-visible cells
  + file integrity.
- **`#US` strings**: Cecil-based patcher. EN byte length ≠ JP byte length is the
  norm → the tool rebuilds the `#US` stream and fixes referencing offsets; same-length
  swaps are the easy path it also handles. **Dry-run first, then apply.**

## 5. QC tracks (the protocol that worked)

Two sequential review tracks, both with the JP source visible on every row:

- **Track S — scenario cells**: review in script/playback order (`lineId`), one
  scenario at a time, doctrine criteria per line (faithfulness, register, POV,
  verb form, beats, quotes). ≈1,900 cells here.
- **Track U — UI/asset fields + DLL `#US`**: build a review table joining every
  EN-ified asset field and every `#US` value to its JP source from the pristine
  build (one row: refid, file, field, jp, en, status). Status per row:
  MATCH / OK:pairs / DIFFERS. Read through in context order; **DIFFERS is the only
  actionable class.**

Rules:

- Review hand-offs show **complete verbatim lines** — trimmed cells read as missing
  content (false "not in JP" flags).
- Fix list → **user approval gate**: nothing applies without sign-off. Approved fixes
  land in the canonical table first, then re-inject through the same pipeline (§4).

## 6. Verify (regression)

- **Always re-extract from the live build.** Stale extraction caches produce apparent
  churn — a 2-field fix once looked like thousands of changes until the cache was
  regenerated from the actual on-disk build.
- **Full-build asset delta** must equal exactly the intended changes and nothing
  else (every file, every field).
- **DLL multiset delta**, not set delta: dedupe collisions (two keys → same value)
  change counts; expected delta = exactly the intended replacements.
- **Structural audit**: type/method count probe identical pre/post
  (e.g. 543 types / 3,833 methods).
- Terminal CJK mojibake is **display-only** (cp932 console) — verify integrity via
  codepoints/dataset-derived keys, never by eye.
- Boot test + in-game playtest with the user; in-game CJK census → 0 visible JP
  except intentionally-baked art pending redraw.

## 7. Failure & rollback

- **Revert first, diagnose second.** A targeted DLL UI patch (auto-height choice
  buttons) shipped "minimal and safe" yet broke clickability. Correct move: restore
  the pristine original file (verify hash), then re-diagnose. Runtime behavior
  (layout builders, event handlers) can silently break even when structure looks fine.
- **Canonical drift is real:** live values can drift from `pairs.txt` with no record
  of it (`Absolutely.` vs `I will.` for the same key). The Track U dataset catches it
  (DIFFERS rows); fix = re-sync to canon + backup, then re-inject.

## 8. UI layout pass (length)

EN is longer than JP: run an auto-resize pass on tight Text/containers (shop,
popups, buttons). Coordinate with the user, apply, verify in-game. Never truncate
meaning to fit — flag overflow instead. Baked-image labels belong to the art track,
not this one.
