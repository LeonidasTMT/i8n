# work/ — scratch (deletable by definition)

Backups, QC runs, per-run workdirs. Anything here must be safe to delete:

- **Regenerable = deletable**: full game-tree copies, per-run extract dumps,
  build artifacts. Keep on disk if you like; never commit; delete after the
  check passes.
- **Verify-run workdirs get cleaned after GREEN**: keep report + log, delete
  the copied tree. Never let copies accumulate across runs.
- Small non-regenerable evidence (reports, before/after dumps of what was
  patched) may live here until promoted to the proper area — but promote it,
  don't let it rot in scratch.
- `archive/` for moves that shouldn't be deleted outright (date-stamped).
