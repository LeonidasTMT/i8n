# Unity (Mono): where text lives

Three containers hold player-visible strings. None is a loose overridable file,
which is why there's no `patch.xp3`-style shadowing.

## 1. Managed assemblies — the `#US` heap
- `<Game>_Data/Managed/*.dll` (e.g. `Assembly-CSharp.dll`) are .NET assemblies.
- Each has a **`#US` heap**: a table of string literals referenced by offset.
  Hardcoded UI text / C# string constants live here.
- Key scheme: `us:<assembly>:<offset>` — deterministic and rejoinable.
- To read: parse the assembly's metadata (`#US`) → (offset, literal).
- To patch natively: replace the bytes at that offset; if the EN byte length ≠ JP
  byte length you must rebuild the `#US` stream and fix every referencing offset,
  then recompute the assembly hash. Same-length swaps are easy; different-length
  is the hard case (see `ENCODING.md`).

## 2. Asset bundles / `.assets`
- A built Unity game packs data into bundles at the game root: `levelN.assets`,
  `sharedassetsN.assets`, and `*.bundle`. These hold scenes, MonoBehaviour
  serialized fields, ScriptableObject tables, TextAssets, TMP font/asset data.
- Serialized in Unity's own binary format, usually compressed; entries are
  content-addressed by hash inside the bundle index. No loose-file override — you
  replace the whole container file.
- Key scheme: `scene:<sha1[:8]>` (or per-container) for scene/MonoBehaviour strings.
- To patch natively: extract the string, re-serialize the asset with EN text, fix
  content hashes, and ship the replaced file.

## 3. Baked images
- Some labels are **painted into textures** (screen headers, chrome). These are
  not text; there's no string to patch. Requires an art pass: dump the texture,
  redraw the label in EN, swap the pixels back. Track separately from text.

## What this means for a "native" patch
The native deliverable is a **patched file set**: replaced managed DLLs, replaced
`.assets`/bundle files, and swapped image textures — dropped into the game over the
originals so it loads EN with no mod. Every one of these is a full-file replacement
of serialized data, not a text edit.
