# 04. translations — catalog, glossary, mapping

- **Catalog** (`catalog/<version_tag>/`): one row per entry — id, host file,
  JP original, EN final, **stage = last stage that wrote the field**, method.
  JSON (machine) + flat CSV export (audit). The catalog is a *human-readable
  projection of `state/`* — generate it, never hand-edit state from here.
- `glossary.md` — locked terms; decisions go in the BIBLE, glossary mirrors
  them.
- Mapping docs: how source identifiers map to segment IDs (stable, permanent).

**Doesn't go here:** per-line review transcripts (`work/qc/`), raw extracts
(`03. extraction/`).
