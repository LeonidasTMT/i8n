# Translation Project Dashboard (template)

Local, single-user HTML dashboard for the Visual Novel Translation Project Operating
Standard: per-line RAW → MTL → TR(Translation) → ED(Editing) → QC → FN(Final) state,
revision history, issue tracking, and release traceability (catalog / state / patcher).

No build step. No network exposure (loopback only). No auth (single-user local tool).
Stdlib-only Python; vanilla JS frontend. Proven on V_ikusei ver2.00 JP→EN (7,662 text
lines, 80 units) — see that project's `management/dashboard/` for a live example.

## Quickstart

```bat
cd management\dashboard
python app\server.py --seed        :: one-time seed from management/project_registers/
python app\server.py               :: serve at http://127.0.0.1:8377
```

- `--reseed` wipes the derived store (`project/`, `history/revisions/*.jsonl`, issues,
  imports) and rebuilds it from the registers. Human edits made through the UI after a
  seed are NOT in the registers and will be lost on reseed — export first if needed.
- `--port N` to change port. `--force` to start even if another server already answers
  on the port (the guard normally refuses so stale servers cannot shadow new ones).
- A fresh template workspace has header-only registers → seeding gives an empty
  dashboard; it fills as the registers fill.

## Per-project configuration

Only two seams, both at the top of `app/server.py`:

- `PROJECT_NAME` — shown in the banner and page title (the h1 comes from seed data).
- Catalog auto-discovery: `/api/releases` picks the **latest** `<stage>/en_catalog.json`
  under `04. translations/catalog/` by mtime. Build your stage catalog into that
  convention; no code change per stage.

Optional inputs (surfaced, not required): `state/*.json`, `05. patcher/patcher.py`,
`management/acceptance_tests.py` (enables `/api/releases/run_acceptance`).

## Layout

```
management/dashboard/
├── app/
│   ├── server.py               # stdlib HTTP backend + static frontend host
│   ├── import_adapters/        # csv / tsv / json → normalized rows
│   └── frontend/               # index.html, app.js (vanilla JS), styles.css
├── project/                    # derived store (safe to delete; rebuilt by --reseed)
│   ├── project.json            # unit registry + line index metadata
│   ├── units/*.json            # one file per unit (unit id ':' → '_' in filename)
│   └── issues.json             # seeded from qc_findings_register.csv
├── history/
│   ├── submissions/SUB-*.json  # seed submission artifacts (evidence, immutable)
│   └── revisions/*.jsonl       # per-unit revision log (seed block + live appends)
├── imports/                    # staged import files (incoming/processed/rejected)
└── releases/                   # acceptance logs + acceptance_last.json
```

Commit the generated store (`project/`, `history/`) as provenance — it is a
projection of the registers, reproducible via `--reseed`, and diffable. Never treat
it as a separate source of truth.

Registers (source of truth, read-only inputs): `management/project_registers/*.csv`.

## Data model

- **Unit** = primary container of a surface: scenario scene (`scn:`), asset pool
  (`pool:`), asset data file (`ast:`), managed DLL (`dll:`), or `rule`.
- **Line** carries per-stage values (`raw`, `mtl`, `tr`, `ed`), stage status map,
  release status, QC state, and provenance notes.
- **Release status** (triage, from `release_line_register.csv`):
  `included` · `untranslated_in_release` · `not_in_native_release` · `excluded_dead`.
  In-scope = `included`; the rest are informational, never "incomplete work".
- **Scope buckets** (computed in `/api/project`): `in_scope`, `oos`
  (= untranslated_in_release + not_in_native_release), `dead_excluded`.
- **Revision** = one value change with stage, submission id, and position. Seed
  revisions are stored as a contiguous positional block per line inside the unit's
  JSONL; live appends carry an explicit `line_id`.
- **Issue** = seeded QC finding (`qc_findings_register.csv`), linked to line/unit.

## Provenance rules (enforced in seed)

1. Register values are canonical: `line_register.EN_FINAL` / `JP_TEXT` win over
   per-line submission rows; no `.strip()` — trailing whitespace is part of the
   shipped value (byte-exact parity with `release_line_register.value_text`).
2. Per-line rows are ordered by SUBMISSION number, not file order.
3. If the last ED row differs from the register final, the line gets a
   `provenance_note` instead of silently picking one side.

## Homepage design conventions (the standard)

- **Hero metric = FINAL % over in-scope lines**, never all rows: OOS and dead lines
  are triage outcomes, not unfinished work. A finished project must read 100%.
- **OOS is an informational footer number** with a `view / re-triage` link to
  `#/lines?cat=out_of_scope` (reclassification stays possible without touching data
  files). Dead lines are excluded from all totals, mentioned only parenthetically.
- **Pipeline = one row per stage with `n / denominator` and %**, plus a semantic tag
  where the stage is partial by design (e.g. MTL "optional machine baseline"). No
  funnel widths — a finished project must not look broken.
- **Attention section collapses to an all-clear state** when every category is zero.
- Every percentage carries its denominator; no bare %. Type scale: hero ~32px
  tabular-nums, secondary counts 18–26px, labels 11–12px uppercase.

## API (all JSON; loopback only)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness + start time |
| GET | `/api/project` | overview: scope, stage counts, attention lists, open issues |
| GET | `/api/units` | unit list with per-state-category counts |
| GET | `/api/unit/{unit_id}` | unit detail (URL-encode `:` as `%3A`) |
| GET | `/api/line/{line_id}` | line detail: values, stages, revisions, issues, context |
| GET | `/api/search?q=...&limit=N` | normalized substring search across raw/tr/ed/mtl |
| GET | `/api/issues` / `/api/issues/{id}` | issue list/detail |
| GET | `/api/imports` / `/api/imports/{id}/preview` | import staging area |
| GET | `/api/releases` | catalog/state/patcher hashes + last acceptance run |

POST: `/api/line/{id}` (value edits), `/api/qc`, `/api/agent/submit`,
`/api/issues` (+ `/{id}/status`, `/{id}/link`), `/api/imports/scan`,
`/api/imports/{id}/apply|reject`, `/api/releases/run_acceptance`
(runs `management/acceptance_tests.py`, stores result + log).

Frontend routes (hash): `#/project`, `#/units`, `#/unit/:uid`, `#/line/:lid`,
`#/issues`, `#/imports`, `#/releases`. Global search box is top-right.

## Windows notes

- Unit ids contain `:` (e.g. `scn:Talk_Lv1`) — invalid in filenames; all per-unit
  files use `unit_filename()` / `unit_revisions_path()` (`:` → `_`).
- `http.server` sets `SO_REUSEADDR`, which on Windows behaves like REUSEPORT and lets
  a stale server share the port with a new one (silent shadowing). The startup probe
  refuses to start while anything answers on the port; kill stale servers first:

```bat
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -like '*server.py*'} | Stop-Process -Force"
```
