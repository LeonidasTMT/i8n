# i8n — JP→EN game translation workflows (cross-reference)

A reference library for **localizing Japanese games to English**, organized by
**engine**. It exists so that future translation jobs can cross-reference an
already-proven pipeline instead of re-deriving it.

Each subfolder is one engine family and contains:
- the reusable **tools** (extract / pack / verify) actually used,
- a **workflow** doc (extract → translate → verify → repack → ship),
- the **format** notes specific to that engine's archives/scripts,
- an **encoding** doc (the #1 trap in JP games), and
- a **QC / lessons-learned** doc (mistakes made, things to look out for).

## Engines

| Folder | Engine | Status |
|--------|--------|--------|
| [`krkr/`](krkr/) | **KiriKiri / KAG** (`.tjs` engine UI, `.ks` scenario, `.txt` story, `data.xp3`) | proven on a shipped patch |

> More engines will be added as they're tackled (e.g. Ren'Py, Tyrano, MML,
> Unity/Mono). The top level stays an index; each engine is self-contained.

## What this repo is / isn't

- **Is:** workflow docs + small reusable Python tools + hard-won QC lessons.
  Small enough to read in one sitting per engine.
- **Isn't:** game content, assets, or the engines' C++ source. No `data.xp3`
  or media is committed here (copyright + size). For engine internals, see
  the upstream sources noted in each folder's README — don't vendor them.

## Ground rules that apply to every engine

> **Above all: translate faithfully.** The author's script is ground truth and
> you are not their editor — see [TRANSLATION.md](TRANSLATION.md) for the full
> doctrine. Everything below assumes it.

1. **Match the original byte-for-byte.** Change only what you intend to change;
   prove it with a diff, not by eye.
2. **Respect the source encoding** (for JP games, almost always CP932/Shift-JIS,
   *not* UTF-8). Round-trip through it and assert it's encodable.
3. **Translate only what the player sees in normal play.** Leave error/debug/
   internal strings alone unless asked.
4. **Preserve functional syntax** (hotkeys, file filters, tags, format
   placeholders) — those are parsed by the engine, not displayed.
5. **Verify by round-trip:** re-extract what you built and diff it against the
   original and against your previous known-good build.
