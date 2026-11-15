# Unity (Mono): where text lives

Three containers hold player-visible strings. None is a loose overridable file,
which is why there's no `patch.xp3`-style shadowing — you replace whole container files.

## 1. Managed assemblies — the `#US` heap
- `<Game>_Data/Managed/*.dll` (e.g. `Assembly-CSharp.dll`) are .NET assemblies.
- Each has a **`#US` heap**: a table of string literals referenced by offset.
  Hardcoded UI text / C# string constants live here (menu labels, confirm dialogs,
  tooltips, log strings).
- Key scheme: `us:<hash>` — deterministic and rejoinable.
- To read: parse the assembly's metadata (`#US`) → (offset, literal).
- To patch natively: replace the bytes at that offset; EN byte length ≠ JP byte
  length is the norm, so expect a **`#US` stream rebuild** + referencing-offset fixup
  + assembly hash recompute. Same-length swaps are the easy path.
- Note: two keys can hold the same value (dedupe) — count strings as a **multiset**
  when diffing, or replacements will look like missing/extra entries.

## 2. Asset bundles / `.assets`
- A built Unity game packs data into files at the game root: `levelN.assets`,
  `sharedassetsN.assets`, `resources.assets`, `*.bundle`. These hold scenes,
  MonoBehaviour serialized fields, ScriptableObject tables, and **TextAssets**.
- Serialized in Unity's own binary format; entries are content-addressed by hash.
  No loose-file override — you replace the whole container file.
- **Two kinds of string fields — know which is which before injecting:**
  - **Display fields** (`...Label`, `...Message`, `text`, choice labels, tooltips):
    player-visible; these get EN.
  - **ID/key reference fields** (story/event/asset IDs, scenario keys, table keys):
    identifiers the engine matches against its tables. **Must stay JP.** EN-ifying
    one breaks scene loading (black screen). Classify by decompiled call-site
    context, not heuristics.
- **Scenario dialogue = CSV `TextAsset` blobs** inside `resources.assets`,
  addressable by pathId — not physical files. "Five scenario CSVs" = five TextAsset
  blobs. Each CSV's `message` column is the exact runtime `.text` string; `lineId`
  order = playback order. Patch at blob level (replace whole CSV bytes),
  structure-preserving (all columns + line breaks intact).
- **`udr.json`** maps to `Resources\unity default resources`, not a top-level file —
  follow the JSON, not the filename.
- Key scheme: `<file>#<field.path>` for string fields; blob index for TextAssets.

## 3. Baked images
- Some labels are **painted into textures** (screen headers, chrome). These are
  not text; there's no string to patch. Requires an art pass: dump the texture,
  redraw the label in EN, swap the pixels back. Track separately from text; they're
  the only allowed exception in the in-game CJK census.

## What this means for a "native" patch
The native deliverable is a **patched file set**: replaced managed DLLs, replaced
`.assets`/bundle files, and swapped image textures — dropped into the game over the
originals so it loads EN with no mod. Every one of these is a full-file replacement
of serialized data, not a text edit.
