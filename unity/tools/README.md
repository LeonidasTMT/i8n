# Unity (Mono) tooling — the actual tools

Generic native-bake toolset: no game data, no hardcoded paths. Source +
Release build committed; deliverable pinned by sha256 below. Built with .NET 9
SDK (`dotnet build -c Release` in each tool dir); deliverables are in
`bin/Release/net9.0/`.

## Managed-DLL toolset (Mono.Cecil-based)

| Tool | What it does | Usage |
|---|---|---|
| `usdump` | Probe a managed assembly's user-string usage: which methods touch given fields, or contain an exact `Ldstr` | `usdump <dll> fields <f1,f2,...>` / `usdump <dll> exact <s1> [s2...]` |
| `ldstrdump` | Dump the `#US` user-string heap (offset → literal) to JSON | `ldstrdump <in.dll> <out.json> [verbose]` |
| `uspatch` | Apply JP→EN replacements in the `#US` stream: rebuild + referencing-offset fixup + assembly hash recompute; dry-run report first, then write | `uspatch <in.dll> <out.dll> <map.json> [report.tsv] [--trace trace.json]` |
| `usref` | Find which assemblies in a Managed dir reference a given string/needle | `usref <managedDir> [needle...]` |
| `ilprobe` | Probe one assembly: types, methods, IL of matching members, enums, call refs | `ilprobe <dll> [--scan <needle>] [--full] [--enum <name>] [--callref <name>]` |
| `ildiff` | Structural diff of two assemblies (pre/post patch) | `ildiff <a.dll> <b.dll>` |
| `typescan` | Fields+methods (with IL instruction counts) of types matching a name substring, incl. nested — the structural audit probe | `typescan <dir> <typeNameSubstring>` |

## Asset toolset

| Tool | What it does | Usage |
|---|---|---|
| `herai` | Extract/inject every string field from `levelN.assets` / `sharedassetsN.assets` / bundles, incl. **TextAsset blob-level** inject (whole-CSV-byte replacement at a blob index). Source committed; no project file — pin the exe by sha256 | see `src/Program.cs` for CLI |
| `herai_ext` | Extended variant on the full AssetsTools.NET stack: per-asset field trees and component scans | `herai_ext.exe uitype tree <file> <pathId>` / `uitype scan <file> [nameFilter]` |

Both asset tools need `classdata.tpk` next to the exe (shipped here).

## Pinned deliverables (sha256)

```
4f617fc7d2924338d9f15c58737f288b0a821680ba1fb55c536baec95d079370  herai/herai-extractinject-unity.exe
129e1f80f930415db6779fe6089afa75280cb51462bcee812beab6cd81a764c6  herai/classdata.tpk
3af2f8a3203cdb818dd2c302d1d91c544ce736a7b3e952dda9d7d5cca7ad270c  usdump/bin/Release/net9.0/usdump.dll
1a30bf23f5f747b4ffbf04855fbf03df1ceb87eb5030f268e24ed7fbef5e69c5  uspatch/bin/Release/net9.0/uspatch.dll
d230f7d324150c4ee1c269bcd73fffe5973eec5d5a0beaf3d1120e11b32bf7d8  usref/bin/Release/net9.0/usref.dll
89986639b73babc01833eac44b21a6474c41e990528210b0b8d50b535d1f5bd0  ldstrdump/bin/Release/net9.0/ldstrdump.dll
afa6200158095e662bcc4c2a76dc086fa41c05ab4ede84eae2cdb04c54353f3d  ilprobe/bin/Release/net9.0/ilprobe.dll
245a140d7999110ceab13cf02cd5d37a5f6a5debb53e36472b26fba5aacd4741  ildiff/bin/Release/net9.0/ildiff.dll
e352e57c9d5c2494679c882d322a02bda1e4c1ea03fd04e0c4a0aa2eb69da7a1  typescan/bin/Release/net9.0/typescan.dll
bb7dab5db12fc331cb8239bb48986a506109cd64cd2c27e4711ff959b68bc9e9  herai_ext/bin/Release/net9.0/herai_ext.dll
9c2908709da6761e9b5b9d4d46102d65851145bac987787d6c5a05ffe5689487  uspatch/bin/Release/net9.0/Mono.Cecil.dll
```

Third-party components and licenses: `NOTICE.md`.
