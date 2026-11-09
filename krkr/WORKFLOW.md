# KiriKiri translation workflow (extract → translate → verify → repack → ship)

Proven end-to-end on a 24-entry `patch.xp3`. Every step has a tool in
[`tools/`](tools/) and a verification gate. The invariant throughout: **only the
bytes you intended change, and you can prove it.**

Paths below assume the game is at `GAME/<game>/` with `data.xp3` inside, and your
working tree under `analysis/`. Adjust freely.

---

## 1. Extract & inventory

```
python tools/xp3_extract.py GAME/data.xp3 analysis/out
```

- Lists every entry with org/arc size. Then find the **text** files (CP932):
  usually `*.txt` (story), `*.ks` (scenario), and a handful of `system/*.tjs`
  (engine UI). Everything else (images, audio, `.dll`, etc.) is left alone.

Inventory questions to answer before translating anything:
- Which files are **player-visible in normal play** vs error/debug/internal?
- Which story files exist (count them — you'll assert the count later)?
- Are there scenario `.ks` that show visible UI (title, menus, CG mode…)?
- Is there a `system/` tree whose files we'd shadow at root level?

## 2. Classify (scope)

Translate **only** player-visible normal-play strings. Deliberately leave in
Japanese:
- error messages, debug menus, console/controller toggles, internal layer names,
  stack-trace-ish text, dev-only prompts.

A single engine file (e.g. `MainWindow.tjs`) often *mixes* both — translate the
player-facing half and leave the rest. When in doubt, leave it and note why.

## 3. Translate with byte-exact CP932 matching

The core pattern (see `tools/build_ui_example.py`): a list of `(old, new)` string
pairs per file, applied to the CP932-decoded text, with a **NO-MATCH safety net**:

```python
for old, new in PAIRS:
    n = text.count(old)
    if n == 0:
        raise SystemExit('NO MATCH: %r' % old)   # aborts before corrupting anything
    text = text.replace(old, new)
```

Rules that make this safe:
- **Never eyeball CJK in the terminal** — it mangles. Dump exact codepoints for
  any ambiguous punctuation (corner brackets `「」`, fullwidth `？ 。 －`, etc.)
  and build the `old` string from those, using `\uXXXX` escapes where you can't
  type it reliably. See [ENCODING.md](ENCODING.md).
- Match on the **full quoted literal** (`"…"`), not a fragment, so you don't hit
  the same text in an unintended place. If a short string legitimately repeats
  (e.g. `はい`/Yes), confirm the count is what you expect and that every hit is
  intended.
- **Preserve functional syntax inside strings:** menu hotkeys `(&S)`, tabs `\t`,
  file-dialog filter specs `(*.bmp)|*.bmp`, KAG tags, format placeholders.
  Change only the human words around them.
- Encode back to CP932 and write bytes; assert it's encodable (it will be if you
  only introduced ASCII/CP932 chars).

## 4. Re-flow story `.txt` to the half-width budget

Japanese is measured in **half-width** units (a kanji = 2). The engine renders a
fixed-width box; English must wrap so no rendered line exceeds that budget (here
≤ 48 half-width chars per segment). See `tools/reflow_example.py`.

The re-flower:
- sources from the **clean pre-reflow backup** (original long lines), never from
  an already-wrapped file → idempotent, no double-wrap;
- applies editorial/translation fixes *before* wrapping;
- collects a block's words in order and greedily wraps at word boundaries to ≤N;
- emits each segment on its own line ending `[r]`, the final one with the block's
  original final tag (`r`/`e1`/`e2`);
- **leaves byte-identical:** embedded-bracket blocks (`[link]`, inline commands)
  and short lines already ≤N (e.g. a lone speaker label), which it keeps on its
  own line.

Get the budget right per game: measure the original box, then assert every prose
segment ≤ budget while *skipping* special-syntax/bracket lines when checking.

## 5. Repack `patch.xp3` (root-level entries shadow originals)

Build an XP3 containing **only** the changed files, at their in-archive path:
bare name for root-level shadowing of `system/*`. See `tools/xp3_pack.py`:

```python
files = [(name, local_path), ...]   # e.g. ('Menus.tjs', '.../Menus.tjs'), ('01.txt', ...)
build_xp3(files, 'patch.xp3')
```

- Story `.txt` and scenario `.ks` go in at their original names (root or the same
  subpath they had, if not shadowing a `system/` file).
- Engine UI `.tjs` go in **bare** (`Menus.tjs`, not `system/Menus.tjs`) so they
  shadow `system/Menus.tjs`.

## 6. Verify (round-trip + only-additions proof)

Re-extract the built archive and check, at least:
- **Entry set** is exactly what you expect (count + names).
- **Every entry decodes as CP932.**
- **Byte/line diff vs the `data.xp3` original:** only intended lines changed, zero
  line-count drift.
- **Only-additions proof:** files you did *not* touch are byte-identical to your
  previous known-good patch (this is the strongest "I didn't break anything"
  check — don't rely on ad-hoc string-presence checks).
- **No JP leftovers** on the player-visible strings you targeted (e.g. scan the
  ribbon `.tjs` for non-ASCII literals → expect 0).

See `tools/verify_example.py` for the concrete version of all four.

## 7. Ship

```
# back up the current shipped patch first (named, per stage)
cp GAME/patch.xp3 analysis/patch_backup_before_<stage>.xp3
cp analysis/patch_new.xp3 GAME/patch.xp3
```

Then **re-verify from disk** the file you actually installed (entry count, CP932,
spot-checks). Never trust a build you didn't re-read after copying.

## Backups: one per stage

Keep a named backup before each repack (`..._before_ks.xp3`,
`..._before_tjs.xp3`, …). They're cheap and let you diff/regress at any step.
