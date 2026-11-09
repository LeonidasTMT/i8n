# Unity (Mono) tooling — categories

This public repo holds methodology only; concrete game-specific tools live in the
instance's own repo. The capability set needed for a native-bake pipeline:

- **`#US` heap dumper + patcher** — read/write the string table in a managed .NET
  assembly (dump offset→literal; write EN, rebuild stream + fix offsets + recompute
  hash when length changes).
- **Asset-bundle / `.assets` extractor + re-serializer** — pull strings from
  scenes/MonoBehaviour/ScriptableObjects/TextAssets and write them back with content
  hashes fixed.
- **UI texture dumper + pixel swapper** — dump baked-image labels for the art pass and
  swap redrawn pixels back (no container surgery).
- **Census / verify harness** — launch, in-game CJK census, byte-diff patched vs
  original, round-trip checks.

Keep game data and proprietary tooling OUT of this repo; only generic approach + small
illustrative stubs belong here.
