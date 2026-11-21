# tools/ — tool sources + pinned binaries

- **Sources committed** for every tool you build (extract/inject, patch, dump,
  diff).
- **Pin by sha256 when there's no version number** (local builds): record the
  hash in this README or in the register that uses the tool. A tool move is
  not done until: file moved, every reference rewritten, live invocation from
  the new location succeeds.
- **Never reference absolute paths outside the repo** — the moment a load-
  bearing artifact lives only in a scratch dir, that's a bug (WORKSPACE.md).
- Deliverable built binaries: force-add that one Release dir on purpose and
  pin it; everything else under `bin/`/`obj/` is ignored.
