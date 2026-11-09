# Encoding: CP932 / Shift-JIS (the #1 trap in JP games)

KiriKiri text files are **CP932 (Shift-JIS)**, *not* UTF-8. Almost every breakage
in this workflow comes from forgetting that. The rules below are non-negotiable.

## Core rules

1. **Decode and re-encode as CP932, always.**
   ```python
   text = raw.decode('cp932')          # read
   blob = text.encode('cp932')         # write — raises if you introduced a non-CP932 char
   ```
   If `encode('cp932')` throws, you put something in the file that can't be
   represented (e.g. an emoji or a UTF-8-only symbol). Fix it before shipping.

2. **Never trust what the terminal shows you.** The console mangles CP932
   output (you'll see `?`, boxes, or wrong glyphs), and different terminals lie
   differently. **Do not eyeball CJK bytes in a shell to decide a match.**

3. **Dump exact codepoints for anything ambiguous.** For punctuation that's easy
   to mistype or that looks identical across scripts, print the codepoint of each
   char and build your search string from those:
   ```python
   s = '」まで戻りますか?'          # as read from the file (CP932-decoded)
   print([hex(ord(c)) for c in s])
   # -> ['0x300d', '0x307e', '0x3067', '0x623b', '0x308a', '0x307e', '0x3059', '0x304b', '0x3f']
   ```
   Then write the match with `\u` escapes so there's no room for a typo:
   `old = '"\u300dまで戻りますか?"'`.

## The punctuation that bites you

These look alike but are different codepoints; get them exactly right:

| Char | Codepoint | Note |
|------|-----------|------|
| `「` / `」` | U+300C / U+300D | CJK corner brackets (often → ASCII `[ ]` in EN) |
| `『` / `』` | U+300E / U+300F | double corner brackets |
| `？` | U+FF1F | **fullwidth** question mark (vs ASCII `?` U+003F) |
| `！` | U+FF01 | fullwidth exclamation |
| `。` | U+3002 | CJK full stop (vs ASCII `.`) |
| `、` | U+3001 | CJK comma |
| `ー` | U+30FC | katakana long vowel |
| `－` | U+FF0D | fullwidth hyphen-minus (vs ASCII `-`) |
| `（）` | U+FF08 / U+FF09 | fullwidth parens |

A real example from this project: I initially read a codepoint dump and mistook
U+623B (`戻`, a kanji) for `も` and U+308A (`ら`) for `ど`. The strings still
matched only after I dumped the exact codepoints. **Lesson: dump, don't guess.**

## Practical technique checklist

- Build each `(old, new)` pair from a **verified** source literal (full quoted
  string), with `\u` escapes for any non-typable punctuation.
- Keep a **NO-MATCH safety net** (`count == 0 → abort`) so a wrong `old` fails
  loudly instead of silently leaving Japanese behind or corrupting bytes.
- If a dump gets truncated in the terminal, **re-dump the full line** before you
  finalize the replacement.
- After building, re-extract and assert: (a) every entry decodes as CP932,
  (b) only intended lines changed vs the original.

## Don't mix the two encodings

- File **contents** = CP932.
- The XP3 index **file names** = UTF-16LE (handled by the packer/extractor).
- Your **report/log files** for humans = write as UTF-8 explicitly so you can read
  them; but the *game* files stay CP932.
