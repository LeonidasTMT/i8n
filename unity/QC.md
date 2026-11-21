# Unity (Mono): QC

## Hard gates

- **Load integrity**: patched managed DLLs still load (assembly hash valid); game
  boots stable; no "Failed:" lines in the loader log. A bad `#US`/asset patch =
  crash or garbled text, so this is a hard gate.
- **Byte-exactness**: per patched container, diff vs original shows ONLY intended
  strings changed; every referencing offset and content hash is consistent;
  round-trip verify each rebuilt `#US` stream / re-serialized asset.
- **Full-build asset delta = intended changes only.** Re-extract *every* file in
  the live build and diff field-by-field vs pristine: the delta must be exactly
  your inject list, nothing else — an only-additions proof.
- **Structural audit**: type/method count probe on patched assemblies identical
  pre/post (e.g. 543 types / 3,833 methods). Catches stream rebuilds that ate or
  duplicated metadata.

## Regression hygiene

- **Always re-extract from the live build.** Stale extraction caches produce
  apparent churn — a 2-field fix once looked like thousands of changes until the
  cache was regenerated from the actual on-disk build. Never regress against an
  old dump.
- **DLL multiset delta**, not set delta: dedupe collisions (two keys → same value)
  change counts; expected delta = exactly the intended replacements, counted.
- **Canonical drift is real:** live values can drift from `pairs.txt` with no record
  of it. The review-table status column catches it (DIFFERS rows); fix = re-sync to
  canon + backup, then re-inject — not a silent hand-edit.
- **Line endings on canonical text tables**: before editing a canonical table
  (e.g. `pairs.txt`), record its line-ending style — CRLF here, and a default LF
  rewrite silently converts every separator. Re-diff vs the backup after writing:
  changed-line count must equal the intended edit count exactly.
- **Terminal CJK mojibake is display-only** (cp932 console). Verify file integrity
  via codepoints/dataset-derived keys, never by eye; run tools with UTF-8 stdout
  (`PYTHONIOENCODING=utf-8`).

## Coverage & quality

- **Coverage census**: in-game CJK census → 0 visible JP, except intentionally-baked
  art still pending the redraw pass. A string is "baked" iff it renders JP now AND
  was never observed as live text.
- **Length/overflow**: EN longer than JP → check UI overflow (checkboxes, lists,
  buttons). Flag for layout; never truncate meaning to fit.
- **Encoding**: UTF-8 no BOM; no mojibake (UTF-8 misread as another codepage); CJK
  raw bytes not `\uXXXX`.

## Sequential review tracks (the protocol that worked)

Both tracks run with the JP source visible on every row, in context order:

- **Track S — scenario cells**: script/playback order (`lineId`), one scenario at a
  time; doctrine criteria per line (faithfulness, register, POV, verb form, beats,
  quotes). ~1,900 cells.
- **Track U — UI/asset fields + DLL `#US`**: review table joining every EN-ified
  asset field and every `#US` value to its JP source from the pristine build
  (row: refid, file, field, jp, en, status). Status classes: MATCH / OK:pairs /
  DIFFERS; **DIFFERS is the only actionable class**.

Rules:

- Review hand-offs show **complete verbatim lines** — trimmed cells read as missing
  content (false "not in JP" flags).
- Fix list → **user approval gate**: nothing applies without sign-off. Approved fixes
  land in the canonical table first, then re-inject through the normal pipeline.
- When a patch misbehaves at runtime: **revert to pristine first** (verify hash),
  then diagnose. Structure can look fine while behavior is broken.

## Honesty

If a string can't be natively baked (length-fragile `#US`, or a baked image), mark
it and route it to the live-fallback / art track — don't silently drop it.
