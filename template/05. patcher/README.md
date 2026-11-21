# 05. patcher — apply-from-final tooling

The patcher consumes **state**, not history: clean install + final-state files
→ patched build. One apply operation per domain (assets / DLL / install-tree),
idempotent, re-runnable on any tree derived from the untouched source.

- **Precheck:** source hashes vs `02. research/sources/source_registry.csv`.
- **Gate:** content-level — re-extract the patched tree and diff against the
  final state (asset side changes layout, so compare *content*, not bytes);
  deterministic hash check where the tool is byte-deterministic (DLL side).
- Per-change delta files are **not** build inputs — they live in git as edit
  history / provenance only.

README here must carry the acceptance evidence (commands run, results, date).
