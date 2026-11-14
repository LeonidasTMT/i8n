# Unity (Mono): QC

- **Load integrity**: patched managed DLLs still load (assembly hash valid); game boots
  stable; no "Failed:" lines in the loader log. A bad `#US`/asset patch = crash or
  garbled text, so this is a hard gate.
- **Byte-exactness**: per patched container, diff vs original shows ONLY intended
  strings changed; every referencing offset and content hash is consistent; round-trip
  verify each rebuilt `#US` stream / re-serialized asset.
- **Line endings on canonical text tables**: before editing a canonical table (e.g.
  `pairs.txt`), record its line-ending style — ikusei's canonical pairs.txt is CRLF,
  and a default LF rewrite silently converts all 4,677 separators. Re-diff vs the
  backup after writing: changed-line count must equal the intended edit count exactly.
- **Coverage census**: in-game CJK census → 0 visible JP, except intentionally-baked
  art still pending the redraw pass. A string is "baked" iff it renders JP now AND was
  never observed as live text.
- **Length/overflow**: EN longer than JP → check UI overflow (checkboxes, lists,
  buttons). Flag for layout; never truncate meaning to fit.
- **Encoding**: UTF-8 no BOM; no mojibake (UTF-8 misread as another codepage); CJK raw
  bytes not `\uXXXX`.
- **Honesty**: if a string can't be natively baked (length-fragile `#US`, or a baked
  image), mark it and route to the live-fallback / art track — don't silently drop it.
