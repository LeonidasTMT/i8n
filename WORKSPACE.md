# Workspace & scratch contract (applies to every project)

`TRANSLATION.md` is the doctrine for *content*. This file is its sibling for
**project structure**: where files live, what may be deleted, and how to keep a
translation workspace auditable. Generalized from the V_ikusei (Unity/Mono)
project; engine-agnostic.

## The contract: straggler-deletability

> **Any file the project requires lives in the designated folders only.**
> If you delete every directory outside the standard tree, the project must
> keep working.

- The **standard tree** is the numbered areas (docs / research / extraction /
  translations / state+patcher / management / releases) plus `tools/` and a
  scratch area. Exact numbering is per-project; the contract is about
  *exclusivity*, not specific numbers.
- **Scratch sandboxes** are allowed but provisional: they must never become
  the *sole home* of a load-bearing artifact (a tool binary, its source, a
  runbook). The moment something required exists only in a scratch dir, that's
  a bug — move it into `tools/` or docs before continuing work.
- **The test**: for every straggler directory ask *"can I delete this?"*
  - **Yes** → candidate for deletion (or harmless to keep).
  - **No** → find what's load-bearing inside, move it into the standard tree,
    rewrite every reference, regression-test, then re-run the test until it
    says yes.

### The herai case (why this rule exists)

The Unity tool `herai-extractinject-unity.exe` lived for weeks in a scratch
sandbox and two live scripts pointed at it by absolute path. Deleting the
sandbox per contract would have broken the pipeline. Fix: moved exe + pdb +
patched source into `tools/herai/`, moved the build runbook into docs, rewrote
the two references, regression-tested (exe runs from the new path). The sandbox
then became pure scratch and was deleted safely.

**General rules derived from it:**

- Pin tools by **sha256** when there's no version number (local builds), and
  reference them by a path *inside* the repo — never an absolute path into a
  scratch dir.
- A tool move is not done until: file moved, every reference rewritten, and a
  live invocation from the new location succeeds.

## Scratch hygiene: evidence vs trash

The 20GB incident: three verify runs each copied the full game `Data` tree
(6.4 GB × 3 ≈ 19 GB) into the workspace as working dirs for content-level
verification. The verifies were GREEN and their reports committed — the copies
were pure regenerable scratch, and the folder had grown to 20 GB, *larger than
the game itself*.

Rules:

- **Regenerable = deletable.** Anything rebuildable from source + final state
  (full game-tree copies, per-run extract dumps, `bin/`/`obj/`) is scratch.
  Keep on disk if you like; never commit it; delete when the check passes.
- **Evidence = small and non-regenerable**: reports, before/after decompiled or
  IL text of *what was patched*, verify logs, final-state JSON. This goes in
  git.
- **Verify-run workdirs get cleaned after GREEN**: keep report + log, delete the
  copied tree. If a verify must copy the whole game tree, budget for it and
  clean up — never let copies accumulate across runs.
- A workspace larger than the game install is always wrong somewhere. Measure
  (`du -sh`) after every big step.

## Repo hygiene (private project repo)

- **No proprietary game data in git**: full `*_Data/` trees, game DLL backups,
  media. Commit *text* evidence instead — decompiled `.cs`, IL dumps, JSON
  state files, reports. (Judgment call: keep the text that proves what was
  patched; drop binaries you can rebuild.)
- **No build artifacts**: `bin/`, `obj/`, vendored deps — *except* when a built
  binary **is** the deliverable tool (then commit that one build dir and pin it
  by sha256).
- `.gitignore` patterns that worked:
  - game-data copies: `<Game>_Data/` at any depth, plus `*.dll` in backup dirs;
  - per-run dumps: `**/cur_extract.json`, per-timestamped-run extract JSONs;
  - artifacts: `bin/`, `obj/`, vendored `.dll` names.
- **Windows reserved names** (`nul`, `con`, `prn`, …) break `git add` and even
  normal deletion, and get created accidentally by shell redirects. Remove them
  with the extended-length path prefix (`\\?\C:\…`). Note: some language
  stdlibs rewrite a trailing reserved name into device form — build that path
  string manually instead of letting a path-normalizer touch it.

## Traceability pattern (what makes a workspace auditable)

Generalized from the ikusei register set:

- **One row per line** in a line register: id, unit, JP source, EN final,
  stage/provenance, status. Everything else (dashboards, reports, release
  manifests) is derived from this.
- **"stage" means "last stage that wrote the field"** — provenance by
  last-writer, not first-seen. Correcting a provenance tag must never change a
  value; if it does, you've edited content, not metadata.
- **Acceptance tests assert only verified facts.** If a claim isn't cheaply
  checkable (e.g., "string X is in file Y"), verify it once forensically, then
  assert exactly what's true — including negative assertions ("not present at
  the live slot"). A test asserting an unverified fact will rot.
- **Dashboard = projection of registers.** Build the UI from register data;
  commit the generated store as provenance so the dashboard is reproducible and
  diffable, not a separate source of truth.
- **Release package = final state + apply tool + acceptance tests.** The
  patcher consumes *state*, not history: clean install + final-state files →
  patched build, gated by content-level re-extract diff (asset side) and
  deterministic hash check (DLL side).

## Checklist before shipping a workspace

- [ ] Every straggler directory answers "can I delete this?" = **yes**
- [ ] No live reference (script or doc) points outside the standard tree
- [ ] `du -sh` on the workspace is sane (≪ game install size)
- [ ] Repo contains no proprietary game data, no build artifacts
- [ ] Registers + acceptance tests pass; dashboard regenerates byte-exact
- [ ] Release area holds final-state files + apply tool + source hashes
