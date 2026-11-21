# Project template — new translation workspace

Instantiation of the standard workspace for a new JP→EN project. Copy this
folder as the **repo root** of the new project, rename, and fill in.

The two governing doctrines live one level up in this library:
`../TRANSLATION.md` (content) and `../WORKSPACE.md` (structure). **Copy both
into `01. docs/` of the new project** — a project repo must not depend on
anything outside itself (straggler-deletability).

## Layout (standard order; numbered for sort)

| Area | Role |
|---|---|
| `01. docs/` | Project docs: pipeline doc, build runbook, adaptation doc, doctrine copies |
| `02. research/` | Research facts + source registry (SHA256 of untouched originals) |
| `03. extraction/` | Extraction workbench: per-stage apply reports, pre/post extracts |
| `04. translations/` | Catalog (per-entry JP→EN with stage provenance), glossary, mapping docs |
| `05. patcher/` | Patcher tooling: clean install + final state → patched build |
| `06. testing/` | `test_cases.csv` + `known_issues.md` + acceptance report |
| `07. releases/` | Release records (one file per release + checksum manifest) |
| `state/` | Final-state files — the single apply input (see its README) |
| `management/` | Registers (CSVs), validation, dashboard projection |
| `tools/` | Tool sources + pinned binaries (sha256 when there's no version number) |
| `work/` | Scratch: backups, QC runs, per-run workdirs. Deletable by definition |

Root files: `AGENTS.md` (workspace contract), plus per-project docs as needed:
README, TRACKER, LESSONS, HANDOFF, TRANSLATOR_BIBLE (style / characters /
locked terms).

## Instantiation checklist

1. Copy this folder → new repo root (keep dotfiles; add `.gitignore`).
2. Copy `../TRANSLATION.md` + `../WORKSPACE.md` into `01. docs/`.
3. Fill in the `AGENTS.md` header: game, engine, version, install paths.
4. Populate `02. research/sources/source_registry.csv` from the untouched
   build — SHA256 of every file you might touch (one-shot; re-run only when
   the source changes).
5. Build tools under `tools/`; pin by sha256; never reference absolute paths
   outside the repo.
6. Keep `work/` clean per WORKSPACE.md: regenerable = deletable; verify-run
   workdirs cleaned after GREEN; workspace must stay ≪ game install size.
7. Run the pre-ship checklist (WORKSPACE.md) before releasing.
