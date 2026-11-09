# Unity (Mono) — JP→EN translation workflow

Engine-agnostic doctrine lives in `../TRANSLATION.md`. This folder is the
**Unity / Mono** specifics: where text is stored, and how to deliver English two
different ways — *live* (runtime mod) vs *native* (baked into the game files).

> Scope note: this covers **Mono** Unity builds (managed C# assemblies on disk).
> **IL2CPP** builds strip the managed assemblies to native code — a different,
> harder case not covered here.

## The two delivery models

| Model | How it works | Pro | Con |
|---|---|---|---|
| **Live** (runtime mod) | A BepInEx plugin hooks Unity's text getters and swaps JP→EN after the string loads | Fast to build; no asset surgery; works today | "Live": replaced at runtime, not baked in; depends on loader+mod booting; not a plain file drop |
| **Native** (baked) | Patch the source containers so the game's own files hold EN; ship a patched file set that replaces originals | No mod; appears native (the KiriKiri `patch.xp3` goal); portable | Hard: must rewrite serialized Unity data + managed DLLs; UTF-8 length changes break offsets/hashes |

**The native model is the target.** It's the Unity analog of KiriKiri's root-level
`patch.xp3`: the game itself contains English, no runtime hook.

## Why there's no `patch.xp3` equivalent in Unity

KiriKiri text is loose files inside an archive you can shadow file-by-file. Unity
text is **not** loose overridable files — it lives inside:

1. **Managed assemblies** (`<Game>_Data/Managed/*.dll`) — a `#US` string heap of
   literals (C# string constants, hardcoded UI text).
2. **Asset bundles / `.assets`** (`levelN.assets`, `sharedassetsN.assets`,
   `*.bundle`) — scenes, MonoBehaviour serialized fields, ScriptableObject tables,
   TextAssets. Serialized binary, compressed, content-hashed.
3. **Baked images** — some labels are painted into textures (headers/chrome); not
   text at all.

So "native" for Unity = produce a **patched file set** (replaced DLLs + replaced
`.assets` + redrawn images) dropped into the game over the originals. That's the
whole job — and it's what makes this harder than KiriKiri. See `FORMAT.md`,
`ENCODING.md`, `WORKFLOW.md`.

## Layout
- `WORKFLOW.md` — extract → triage → translate → **native re-bake** → verify
- `FORMAT.md` — where Unity stores text (DLL #US heap, asset bundles, baked images)
- `ENCODING.md` — UTF-8 and the byte-length problem
- `QC.md` — Unity-specific verification
- `tools/README.md` — tooling categories needed

## Reference instance
A concrete Mono-Unity instance of this pipeline exists in its own (private) repo;
this folder is the reusable methodology only — no game data here.
