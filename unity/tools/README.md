# Unity (Mono) tooling — categories

This public repo holds methodology only; concrete game-specific tools live in the
instance's own repo. The capability set needed for a native-bake pipeline, as
proven on a full JP→EN build:

- **Asset extractor + injector** — dump every string field from `levelN.assets` /
  `sharedassetsN.assets` with its path (key `<file>#<field.path>`), assert the id
  set is identical between JP/EN builds, and inject byte-exact replacements where
  non-target strings come back unchanged. Must also handle **TextAsset blob-level
  inject**: replace whole CSV bytes at a blob index inside `resources.assets`
  (scenario dialogue lives there, not in loose files).
- **`#US` heap dumper + Cecil-based patcher** — read the string table in a managed
  .NET assembly (dump offset→literal); write EN with stream rebuild + referencing-
  offset fixup + hash recompute when length changes. Dry-run mode first, then apply;
  decompile-verify after.
- **Structural probe** — type/method counts on patched assemblies, compared pre/post,
  to prove a patch didn't eat or duplicate metadata.
- **Census / verify harness** — live re-extract (never stale caches), dataset join of
  every EN value to its JP source from the pristine build with per-row status
  (MATCH / OK:pairs / DIFFERS), full-build field delta, DLL multiset delta, in-game
  CJK census.

Keep game data and proprietary tooling OUT of this repo; only generic approach +
small illustrative stubs belong here.
