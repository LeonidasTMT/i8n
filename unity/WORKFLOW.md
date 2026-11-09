# Unity (Mono): JP→EN workflow (native-bake target)

Doctrine: `../TRANSLATION.md`. The stages below produce a **patched file set** the
game loads natively — no runtime mod. The live BepInEx path is the pragmatic fallback
where native-bake is infeasible for a string class.

## 1. Extract
- **Managed DLL `#US` heap**: per assembly, dump (offset → JP literal). Key
  `us:<assembly>:<offset>`.
- **Asset bundles / `.assets`**: extract string blobs from scenes/MonoBehaviour/
  ScriptableObjects/TextAssets. Key `scene:<sha1[:8]>`.
- **Baked images**: dump UI textures for the art pass (separate track).
- Provenance-first: reverse-search a known in-game string against the containers to
  confirm which one actually holds it before editing.

## 2. Triage
- Classify by **decompiled call-site context**, not heuristics: user-visible text vs
  internal/log/debug vs baked-image label. Use decompiled source for context.
- Decide per string: native-bake (DLL/asset) vs art-pass (baked image) vs skip
  (internal).

## 3. Translate
- Same doctrine as `../TRANSLATION.md`: faithful, character pass, pronoun/reference
  resolution, honorifics preserved, structure/markers intact, ambiguity rules.
- Emit a canonical table: key → EN (UTF-8 no BOM). One source of truth; everything
  else is derived from it.

## 4. Native re-bake (the Unity-specific step)
For each translated string, write EN into the source container and ship the replaced
file:
- **`#US` strings**: patch the managed DLL. Same byte length → in-place swap.
  Different length → rebuild the `#US` stream, fix referencing offsets, recompute the
  assembly hash. Ship the replaced `.dll`.
- **Asset strings**: re-serialize the `.assets`/bundle with EN text, fix content
  hashes, ship the replaced file.
- **Baked images**: redraw EN onto the dumped texture, swap pixels back (art pass).

Result: a patched file set dropped into the game over the originals → native EN.

## 5. Verify
- Launch stable; no "Failed:" lines in the loader log.
- **In-game CJK census** → 0 visible JP (except intentionally-baked art pending redraw).
- **Byte diff vs original**: only intended strings changed; offsets/hashes consistent;
  round-trip verify each patched container.
- Overflow pass for lengthened EN strings.

## Fallback: live runtime mod (when native-bake isn't viable)
A BepInEx plugin can hook Unity text getters and swap JP→EN at runtime from a table —
fast to build, no asset surgery. Use it as the fallback for classes that can't be
natively baked (length-fragile `#US` entries, baked images awaiting art). It's "live"
(replaced after load) and depends on the loader+mod booting — so it's a stopgap, not
the target. A mod must never silently drop a string; log near-misses.
