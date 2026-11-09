# Unity (Mono): encoding and the byte-length problem

## Encoding: UTF-8
- Managed `#US` strings and asset-bundle strings are **UTF-8** (contrast KiriKiri's
  CP932/Shift-JIS). No BOM. CJK stored as raw UTF-8 bytes, not `\uXXXX`.
- If you emit any text sidecar (e.g., a translation table), use UTF-8 no BOM and run
  tools with UTF-8 stdout (`PYTHONIOENCODING=utf-8`) to avoid cp932 console mojibake.

## The byte-length problem (the crux)
- In UTF-8, a JP CJK character is **3 bytes**; an EN ASCII letter is **1 byte**. A
  typical JP→EN line changes length a lot (often longer in EN).
- Consequence: an EN replacement is almost **never** the same byte length as the JP
  source. That breaks the two cheap native-patch tricks:
  - **Same-offset, same-length in-place patch** works only when lengths match — rare.
  - Otherwise you must **rebuild the container**: rewrite the `#US` stream (and fix
    every referencing offset + assembly hash) or re-serialize the asset (and fix its
    content hash). This is why Unity native-bake is far harder than KiriKiri's file
    shadowing, where length changes are free.
- Budget for this: per string you may need a container rebuild, not a byte swap.

## Overflow
- Because EN is usually longer, watch UI overflow (checkboxes, lists, buttons). Flag
  overflows for a layout pass; don't silently truncate meaning to fit.
