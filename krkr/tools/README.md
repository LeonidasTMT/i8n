# Tools

Python 3, no external deps (stdlib only). `xp3_extract.py` and `xp3_pack.py` are
**generic** — they work on any KiriKiri `.xp3`. The other three are **reference
implementations** from a real project: the reusable logic is what matters; the
constants at the top of each (paths, file lists, string pairs) are per-game and
should be edited for your target.

| File | Generic? | What it does |
|------|----------|--------------|
| `xp3_extract.py` | ✅ yes | Open a `.xp3`; list entries; extract one or all to disk. Handles the index chain, raw+zlib segments, `FindChunk`. |
| `xp3_pack.py` | ✅ yes | Build a **raw** (uncompressed) `.xp3` byte-compatible with the engine reader from a list of `(arc_name, local_path)`. |
| `reflow_example.py` | ⚙️ example | Re-wrap story `.txt` to ≤N half-width chars; keeps speaker labels + `[link]`/command blocks byte-identical. Edit `CUR`, `KS_NAMES`, `UIDIR`, `MAXSEG`, `FIXES`. |
| `build_ui_example.py` | ⚙️ example | Apply `(old,new)` string pairs to `.tjs`/`.ks` UI with a NO-MATCH safety net + CP932 round-trip. Edit `SRC` and the pair lists (`MENUS`, `MAINWINDOW`, …). |
| `verify_example.py` | ⚙️ example | Round-trip verify: entry set, CP932 decode, byte-identical untouched files vs prior patch, JP-leftover scan. Edit the paths + expected sets. |

## Minimal usage (generic tools)

```
# list + extract an archive
python xp3_extract.py path/to/data.xp3 out_dir

# build a patch from changed files (arc_name=local_path), root-level to shadow system/
python xp3_pack.py patch.xp3 "Menus.tjs=build/Menus.tjs" "01.txt=build/01.txt"
```

`xp3_pack.py` takes `arc_name=local_path` pairs on the command line; in code, call
`build_xp3([(name, path), ...], out)` directly (that's what the example builders do).
