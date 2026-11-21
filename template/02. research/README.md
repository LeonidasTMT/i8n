# 02. research — facts + source registry

What the game is, and exactly what its untouched files are.

- `sources/source_registry.csv` — **SHA256 of every untouched source file**
  you might touch (header: `SOURCE_ID,relpath,size_bytes,sha256`). One-shot
  generated from the pristine install; re-run only when the source version
  changes. This is the integrity baseline everything else diffs against.
- Engine facts: where text lives, which files are content-hashed, layout
  notes, anything learned by RE that other areas rely on.

**Doesn't go here:** decompiled dumps and extracts (evidence goes to
`03. extraction/` or `work/`).
