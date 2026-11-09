# KiriKiri `.xp3` archive format + patch override mechanics

The tools in [`tools/`](tools/) mirror this exactly; this doc explains *why* so
you can adapt them if a given game's archive differs.

## XP3 binary layout (raw, uncompressed — what `xp3_pack.py` emits)

```
[0..10]   mark  'X','P','3',0x0d,0x0a,' ',0x0a,0x1a,0x8b,0x67,0x01
          (bytes: 58 50 33 0d 0a 20 0a 1a 8b 67 01)
[11..18]  I64LE index_ofs   = offset of the index block from archive start
[19 .. ]  file data segments (raw, contiguous)
[index_ofs..] index block:
    1 byte flag            (0x00 = raw, no-continue; low3 = encode method, bit7 = continue)
    I64LE idx_size         + index bytes
```

The **index** is a sequence of `File` chunks. A "chunk" is `[4s tag][I64LE size]
[payload]`. Each `File` payload contains sub-chunks (scanned in order by the
`FindChunk` walk):

- `info`: `I32 flags, I64 OrgSize, I64 ArcSize, I16 name_len, UTF-16LE name`
- `segm`: N × 28-byte records: `I32 flags, I64 Start, I64 OrgSize, I64 ArcSize`
  (flags low3: 0 = raw, 1 = zlib; `Start` is relative to archive start)
- `aldr`: `I32 FileHash`

Notes that matter when packing:
- Names are **UTF-16LE** in the index even though file *contents* are CP932 —
  don't confuse the two encodings.
- A raw (uncompressed) archive is byte-compatible with what the engine's reader
  expects; we verified against the game's own `data.xp3` + our extractor.
- The index can be a **chain** (the `continue` bit links another index block);
  the extractor handles it, the packer writes a single raw block.
- Some archives are MZ-prefixed executables with the mark at an aligned offset;
  the extractor here only supports the plain form (raises otherwise).

## Why root-level entries shadow `system/` files (the override trick)

KiriKiri keeps an ordered list of archive/search paths and resolves a file by
scanning it **most-recently-added first**. At startup the engine does:

```
useArchiveIfExists("patch.xp3")   // appends "patch.xp3>" to the path, after system/
```

Consequences:
- `patch.xp3>` is searched *before* `system/`, so a root-level `Menus.tjs` in the
  patch wins over `system/Menus.tjs`.
- A bare (root) entry name shadows any same-named file anywhere earlier on the
  path. That's how we override engine `.tjs`, scenario `.ks`, and story `.txt`
  without touching `data.xp3`.
- Files **not** in the patch are simply found at their original location, so all
  non-text assets (images/audio/code) keep working untouched.

So a patch is just "the set of changed files, at the path that shadows the
original." Root-level = shadow `system/`; use the original subpath only when you
must not collide with something you want to keep.

## Practical invariants for a correct patch

- Entry names must be **exactly** the in-archive paths you intend to shadow
  (bare name for `system/` files).
- Contents must be **CP932** (the engine reads them as such).
- Only changed files are included; everything else is inherited from
  `data.xp3`.
