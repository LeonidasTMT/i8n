# 03. extraction — workbench

Per-stage extraction and apply evidence. Each stage leaves:

- **Apply report** (TSV or MD): tool, exact command, inputs/outputs, results,
  verification method — this *is* the extraction manifest of record.
- Pre/post extract JSONs where they're the small, non-regenerable proof; big
  regenerable dumps stay in `work/` and get deleted after the check passes.

**Doesn't go here:** translations (that's `04. translations/`), full game-tree
copies (never — see WORKSPACE.md scratch hygiene).
