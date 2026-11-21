# management/ — registers, validation, dashboard

The traceability layer. **One row per line** in `project_registers/line_register.csv`;
everything else (dashboards, reports, release manifests) is derived from the
registers.

- `project_registers/*.csv` — header-only here; fill as work happens:
  - `source_registry` / `file_register` / `asset_inventory` — what exists
  - `extraction_registry` — every extraction run (tool, procedure, verification)
  - `line_register` — the spine: id, surface, JP source, EN final, status
  - `submission_register` + `submission_line_register` — every stage that
    wrote values (stage = last-writer on the line register)
  - `qc_findings_register` — findings → resolution with reviewer + evidence
  - `release_register` + `release_line_register` — what shipped, per line
  - `contributors` / `validation_report` — who + integrity checks
- Validation: a script that re-hashes and cross-checks every register;
  results land in `validation_report.csv`.
- `dashboard/` — the local HTML dashboard app (stdlib-only Python + vanilla JS).
  `python app/server.py --seed` once per project, then serve; commit the generated
  store as provenance.
- **Dashboard = projection of registers.** Build the UI from register data;
  commit the generated store as provenance so it's reproducible and diffable —
  never a separate source of truth.
