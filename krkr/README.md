# KiriKiri / KAG (`.tjs` / `.ks` / `.txt`, `data.xp3`)

**KiriKiri** ("kag") is a visual-novel engine. Its scripts use the `KAG*` class
family (`KAGMenu`, `KAGMenuItem`, …), which is why the code reads as KAG even
when files carry `.tjs` extensions. Everything below was proven on a real
shipped patch (14 story scenes + 6 scenario UI scripts + 4 engine UI scripts,
24-entry `patch.xp3`).

## Where text lives in a KiriKiri game

| Path (inside `data.xp3`) | What it is | Text? |
|---|---|---|
| `system/*.tjs` | **Engine** UI: ribbon/menus, main window, save/load, history, dialogs | yes — player-visible menus & prompts |
| `scenario/*.ks`, `*.ks` | **Scenario** scripts the author wrote (title, CG mode, volume, macros, first scene…) | yes — visible scenario UI strings |
| root / subfolder `*.txt` | **Story** scenes (narration + dialogue) with KAG line tags | yes — the actual story |
| `*.tjs` under `system/` only for engine code; story is `.txt` in this layout | | |

> Layouts vary per game. Always extract and *inventory* first (see
> [WORKFLOW.md](WORKFLOW.md)) before assuming where text lives.

### Story line tags (`.txt`)

- `[r]` — end of a rendered line (line break).
- `[e1]` / `[e2]` — block-end markers; the **last** tag in a run is preserved.
- A "block" = consecutive lines each ending in one of those tags.
- Speaker labels sit on their own short line at the start of a block.
- `[link]…[/link]` and inline commands must stay **byte-identical**.

## The patch / override mechanism (how we ship without touching `data.xp3`)

KiriKiri resolves files by searching its archive path list, **most-recently-added
first**. The engine startup calls:

```
useArchiveIfExists("patch.xp3")
```

which appends `patch.xp3>` to the search path *after* `system/`. Because the
most recent path wins, a **root-level** entry in `patch.xp3` shadows any file of
the same name under `system/` (or anywhere else on the path). That's the whole
trick:

- Put a translated `Menus.tjs` at the **root** of `patch.xp3` → it shadows
  `system/Menus.tjs`.
- Story `.txt` and scenario `.ks` are shadowed the same way (bare name = root).
- Non-text assets are simply *not* included, so the originals are used.

So a patch is just an XP3 archive of **only the files we changed**, at their
original in-archive path (bare name for root-level shadowing). See
[FORMAT.md](FORMAT.md) for the binary layout and why root-level shadows work.

## Quick start

1. Extract `data.xp3` → inventory text files.  [WORKFLOW.md §1](WORKFLOW.md)
2. Classify player-visible vs internal.                                  §2
3. Translate with byte-exact CP932 matching (NO-MATCH safety net).     §3
4. Re-flow story `.txt` to the half-width budget.                      §4
5. Repack `patch.xp3` (root-level entries shadow originals).           §5
6. Verify (round-trip + only-additions proof).                        §6
7. Ship: back up current patch, install, re-verify from disk.          §7

Tools in [`tools/`](tools/):
- `xp3_extract.py` — read any `.xp3` (list / extract files).
- `xp3_pack.py` — build a raw XP3 byte-compatible with the game's reader.
- `reflow_example.py` — story re-wrap to ≤N half-width chars (per-game constants at top).
- `build_ui_example.py` — string-replacement harness for `.tjs`/`.ks` UI (pairs are game-specific).
- `verify_example.py` — round-trip + only-additions verification.

## Encoding

KiriKiri text is **CP932 / Shift-JIS**, not UTF-8. This is the #1 source of
breakage. See [ENCODING.md](ENCODING.md).

## Engine internals (don't vendor, just reference)

- `krkr2` (original KiriKiri 2, C++) — e.g. `core/base/XP3Archive.cpp` for the
  archive format this repo's tools mirror.
- `krkrz` (a maintained variant) — `base/`, `tjs2/` (the TJS engine).
Keep these as local reference only; they're third-party GPL and large.
