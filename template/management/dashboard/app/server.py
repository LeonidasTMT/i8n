#!/usr/bin/env python3
"""Translation project dashboard (i8n template) — local backend + static frontend.

Design principle: the dashboard presents the work; this backend manages the
records, history and workflow rules. The browser never implements workflow
logic and never reads canonical files directly.

Run:
    python app/server.py            # serve on http://127.0.0.1:8377
    python app/server.py --seed     # one-time seed from project registers
    python app/server.py --port 8390

Stdlib only. Single user, loopback-only (no auth by design; binds 127.0.0.1).
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import unicodedata
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# --------------------------------------------------------------------------- paths

APP_DIR = Path(__file__).resolve().parent            # .../management/dashboard/app
DASH_ROOT = APP_DIR.parent                            # .../management/dashboard
WS_ROOT = DASH_ROOT.parent.parent                     # workspace root
FRONTEND_DIR = APP_DIR / "frontend"

PROJECT_DIR = DASH_ROOT / "project"
UNITS_DIR = PROJECT_DIR / "units"
HISTORY_DIR = DASH_ROOT / "history"
REVISIONS_DIR = HISTORY_DIR / "revisions"
SUBMISSIONS_DIR = HISTORY_DIR / "submissions"
TRANSACTIONS_DIR = HISTORY_DIR / "transactions"
IMPORTS_DIR = DASH_ROOT / "imports"
INCOMING_DIR = IMPORTS_DIR / "incoming"
PROCESSED_DIR = IMPORTS_DIR / "processed"
REJECTED_DIR = IMPORTS_DIR / "rejected"
EXPORTS_DIR = DASH_ROOT / "exports"
RELEASES_DIR = DASH_ROOT / "releases"

REGISTERS_DIR = WS_ROOT / "management" / "project_registers"
CATALOG_DIR = WS_ROOT / "04. translations" / "catalog"


def find_catalog():
    """Latest stage catalog: <stage>/en_catalog.json under 04. translations/catalog (by mtime)."""
    if not CATALOG_DIR.exists():
        return None
    cands = list(CATALOG_DIR.glob("*/en_catalog.json"))
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None
STATE_DIR = WS_ROOT / "state"
PATCHER_DIR = WS_ROOT / "05. patcher"
ACCEPTANCE_SCRIPT = WS_ROOT / "management" / "acceptance_tests.py"

PROJECT_FILE = PROJECT_DIR / "project.json"
ISSUES_FILE = PROJECT_DIR / "issues.json"
IMPORTS_META_FILE = IMPORTS_DIR / "imports.json"
TRANSACTIONS_LOG = TRANSACTIONS_DIR / "recent.jsonl"

STAGES = ["RAW", "MTL", "TR", "ED", "QC", "FN"]
PROJECT_NAME = "Translation project"  # set for your project (shown in the header)
PORT_DEFAULT = 8377
HOST = "127.0.0.1"

for d in (PROJECT_DIR, UNITS_DIR, REVISIONS_DIR, SUBMISSIONS_DIR, TRANSACTIONS_DIR,
          INCOMING_DIR, PROCESSED_DIR, REJECTED_DIR, EXPORTS_DIR, RELEASES_DIR):
    d.mkdir(parents=True, exist_ok=True)

LOCK = threading.RLock()


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha10(s):
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()[:10]


def norm_text(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.casefold()


def unit_filename(unit_id):
    """Windows-safe filename for a unit (unit ids contain ':')."""
    return unit_id.replace(":", "_") + ".json"


def unit_revisions_path(unit_id):
    return REVISIONS_DIR / (unit_id.replace(":", "_") + ".jsonl")


def atomic_write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
    if path.exists():
        bak = path.with_name(path.name + ".bak")
        try:
            shutil.copy2(str(path), str(bak))
        except OSError:
            pass
    os.replace(tmp, path)


def read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except (json.JSONDecodeError, OSError):
        bak = Path(str(path) + ".bak")
        if bak.exists():
            with open(bak, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        raise


# --------------------------------------------------------------------------- store

class Store:
    def __init__(self):
        self.project = None
        self.units = {}          # unit_id -> {unit_id, surface, name, line_order, lines}
        self.line_index = {}     # line_id -> (unit_id, line)
        self.issues = {"next_issue_no": 1, "issues": {}}
        self.imports = {"next_import_no": 1, "imports": {}}

    def load(self):
        if not PROJECT_FILE.exists():
            raise SystemExit(
                "project store not seeded yet — run: python app/server.py --seed")
        self.project = read_json(PROJECT_FILE)
        for unit_id in self.project.get("units", {}):
            data = read_json(UNITS_DIR / unit_filename(unit_id))
            if data is None:
                raise SystemExit(f"missing unit file for {unit_id}")
            self.units[unit_id] = data
            for lid, line in data["lines"].items():
                self.line_index[lid] = (unit_id, line)
        self.issues = read_json(ISSUES_FILE, {"next_issue_no": 1, "issues": {}})
        self.imports = read_json(IMPORTS_META_FILE, {"next_import_no": 1, "imports": {}})
        return self

    def save_unit(self, unit_id):
        atomic_write_json(UNITS_DIR / unit_filename(unit_id), self.units[unit_id])

    def save_issues(self):
        atomic_write_json(ISSUES_FILE, self.issues)

    def save_imports(self):
        atomic_write_json(IMPORTS_META_FILE, self.imports)

    def append_revision(self, unit_id, entry):
        path = unit_revisions_path(unit_id)
        with open(path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def record_transaction(self, tx):
        tx["tx_id"] = "TX-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
        tx["ts"] = now_iso()
        with open(TRANSACTIONS_LOG, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(tx, ensure_ascii=False) + "\n")
        return tx["tx_id"]

    def recent_transactions(self, limit=15):
        if not TRANSACTIONS_LOG.exists():
            return []
        out = []
        with open(TRANSACTIONS_LOG, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out[-limit:]


STORE = None  # set on start/seed

# --------------------------------------------------------------------------- workflow

def derived_state(line):
    """Derive the actionable workflow state of a line from its record.

    Returns (category, detail). Categories:
      final, awaiting_translation, awaiting_edit, awaiting_qc,
      needs_revision, out_of_scope, empty
    """
    if not (line.get("raw") or "").strip():
        return "empty", ""
    open_f = len(line.get("qc", {}).get("open_findings", []))
    stale = line.get("stale", [])
    if stale or open_f:
        why = []
        if stale:
            why.append("stale:" + "+".join(stale))
        if open_f:
            why.append(f"{open_f} open finding(s)")
        return "needs_revision", "; ".join(why)
    rel = line.get("release_status", "")
    tr_done = line["stages"]["TR"] in ("done", "scene")
    has_tr = bool((line.get("tr") or "").strip())
    has_ed = bool((line.get("ed") or "").strip())
    if rel == "included":
        # an edited final (ed) implies the translation exists and was edited,
        # so it satisfies both the TR and ED gates
        if not (has_tr or has_ed or tr_done):
            return "awaiting_translation", "no TR/ED value recorded"
        if not has_ed:
            return "awaiting_edit", "TR present, no edited final yet"
        qc = line.get("qc", {}).get("state", "none")
        if qc in ("pending", "stale"):
            return "awaiting_qc", f"QC {qc}"
        return "final", ""
    return "out_of_scope", rel or "no release status"


ATTENTION_ORDER = ["needs_revision", "awaiting_translation", "awaiting_edit", "awaiting_qc"]


def apply_line_change(store, line_id, fields, actor, note="", base_rev=None, force=False):
    """Apply a field change to one line through the workflow engine.

    fields: dict with any of raw/mtl/tr/ed (values), speaker/note (metadata only).
    Returns result dict; never raises for conflict/noop cases.
    """
    hit = store.line_index.get(line_id)
    if not hit:
        return {"status": "not_found", "line_id": line_id}
    unit_id, line = hit
    changes = {}
    for k in ("raw", "mtl", "tr", "ed"):
        if k in fields and fields[k] is not None:
            newv = fields[k]
            if newv != (line.get(k) or ""):
                changes[k] = newv
    meta_only = {}
    for k in ("speaker",):
        if k in fields and fields[k] is not None and fields[k] != (line.get(k) or ""):
            meta_only[k] = fields[k]

    if base_rev is not None and base_rev != line["rev"]:
        return {"status": "conflict", "line_id": line_id,
                "expected_base_rev": line["rev"], "submitted_base_rev": base_rev}
    if force and base_rev is not None and base_rev != line["rev"]:
        pass  # explicit force: proceed (recorded in transaction)

    if not changes and not meta_only:
        return {"status": "noop", "line_id": line_id, "rev": line["rev"],
                "effects": ["no-op: submitted values identical; no revision created"]}

    unit = store.units[unit_id]
    rev_before = line["rev"]
    effects, revisions = [], []
    ts = now_iso()
    sub_ref = note  # free-form reference (e.g. SUB-DASH-001) carried in history

    for field in ("raw", "mtl", "tr", "ed"):
        if field not in changes:
            continue
        line["rev"] += 1
        line[field] = changes[field]
        rev_no = line["rev"]
        revisions.append({
            "ts": ts, "actor": actor, "stage": field.upper(), "field": field,
            "value": changes[field], "sha10": sha10(changes[field]),
            "rev": rev_no, "submission_id": sub_ref, "note": note,
            "line_id": line_id,
        })
        if field == "raw":
            line["stages"]["RAW"] = "done"
            line["stale"] = ["TR", "ED", "QC", "FN"]
            effects.append("RAW changed → TR/ED/QC/FN require reassessment")
        elif field == "mtl":
            line["stages"]["MTL"] = "done"
            effects.append("MTL baseline updated (reference only; no downstream invalidation)")
        elif field == "tr":
            line["stages"]["TR"] = "done"
            if (line.get("ed") or "").strip():
                line["stale"] = ["ED", "QC"]
                line["ed_reviewed_tr_rev"] = None
                effects.append("TR changed → ED requires reconciliation; QC review stale")
            else:
                line["stale"] = []
                effects.append("TR recorded (no downstream values yet)")
        elif field == "ed":
            line["stages"]["ED"] = "done"
            if line.get("qc", {}).get("state") in ("passed",):
                line["stale"] = ["QC", "FN"]
                effects.append("ED changed → previous QC approval no longer applies to this revision; re-QC required")
            else:
                line["stale"] = ["QC"] if line["stages"]["QC"] in ("passed", "attention") else []
                effects.append("ED changed → QC review required")
            line["qc"]["state"] = "pending"

    for k, v in meta_only.items():
        line[k] = v
        effects.append(f"metadata-only update: {k} (no revision, no invalidation)")

    if changes:
        # clear stale flags for stages that now have fresh values
        still_stale = []
        for s in line.get("stale", []):
            if s == "TR" and "tr" in changes:
                continue
            if s == "ED" and "ed" in changes:
                continue
            still_stale.append(s)
        line["stale"] = still_stale
    line["updated_at"] = ts

    for r in revisions:
        store.append_revision(unit_id, r)
    store.save_unit(unit_id)
    return {"status": "applied", "line_id": line_id, "rev_before": rev_before,
            "rev_after": line["rev"], "changes": list(changes), "effects": effects}


def qc_action(store, line_id, verdict, actor, note=""):
    hit = store.line_index.get(line_id)
    if not hit:
        return {"status": "not_found", "line_id": line_id}
    unit_id, line = hit
    ts = now_iso()
    if verdict == "pass":
        line["qc"]["state"] = "passed"
        line["qc"]["pinned_ed_rev"] = line["rev"]
        tr_done = line["stages"]["TR"] in ("done",)
        line["ed_reviewed_tr_rev"] = line.get("tr_rev") if tr_done else None
        line["stages"]["QC"] = "passed"
        line["stale"] = [s for s in line.get("stale", []) if s not in ("QC",)]
        effect = f"QC passed: approval pinned to ED revision {line['rev']}"
    elif verdict == "fail":
        line["qc"]["state"] = "failed"
        line["stages"]["QC"] = "attention"
        effect = "QC failed: correction required before FN"
    else:
        return {"status": "bad_verdict"}
    store.append_revision(unit_id, {
        "ts": ts, "actor": actor, "stage": "QC", "field": None,
        "value": verdict, "sha10": "", "rev": line["rev"],
        "submission_id": None, "note": note, "line_id": line_id,
    })
    store.save_unit(unit_id)
    return {"status": "applied", "line_id": line_id, "effect": effect}


# --------------------------------------------------------------------------- seed

POOL_SOURCE_NAMES = {
    "ui-systems": "UI systems pool",
    "hscenes": "H-scenes pool",
    "fan-comments": "Fan comments pool",
    "monologue": "Monologue pool",
    "vtuber": "VTuber pool",
}


def _sub_num(sid):
    return int(re.sub(r"\D", "", sid) or 0)


def _csv_rows(name):
    import csv as _csv
    _csv.field_size_limit(10 * 1024 * 1024)
    with open(REGISTERS_DIR / name, "r", encoding="utf-8-sig", newline="") as f:
        return list(_csv.DictReader(f))


def unit_for_line(line_row, file_map=None):
    surface = line_row["SURFACE"]
    lid = line_row["LINE_ID"]
    if surface == "scenario":
        scene = line_row.get("SCENARIO_ID") or "?"
        return f"scn:{scene}", "scenario", scene
    if surface == "asset_pool":
        m = re.search(r"registry:([\w-]+)\.tsv", line_row.get("NOTES", ""))
        src = m.group(1) if m else "other"
        name = POOL_SOURCE_NAMES.get(src, src)
        return f"pool:{src}", "asset_pool", name
    if surface == "asset_field":
        m = re.match(r"LN-AST-F-(.+)$", lid)
        f = m.group(1).split("#")[0] if m else "?"
        return f"ast:{f}", "asset_field", f
    if surface == "dll":
        fid = line_row.get("FILE_ID", "")
        if file_map and fid in file_map:
            f = file_map[fid]
        else:
            rest = lid[len("LN-DLL-"):]
            f = re.sub(r"-us[0-9a-f]+$", "", rest) or "?"
            f += ".dll"
        return f"dll:{f}", "dll", f
    if surface == "rule":
        return "rule", "rule", "BepInEx-era rules (historical)"
    return f"{surface}:?", surface, surface


def seed_project():
    """One-time seed: build the app store from the project registers.

    Canonical-after-seed = this store. Registers remain as frozen evidence
    for the seed moment and regenerate as exports.
    """
    if PROJECT_FILE.exists() and not (PROJECT_FILE.parent / "units").glob("*.json"):
        pass
    if PROJECT_FILE.exists():
        print("project store already exists; use --reseed to rebuild from registers")
        return

    lines = _csv_rows("line_register.csv")
    file_map = {}
    for fr in _csv_rows("file_register.csv"):
        p = fr.get("path_or_label", "")
        if p:
            file_map[fr["FILE_ID"]] = p.rsplit("/", 1)[-1]
    rels = {r["LINE_ID"]: r for r in _csv_rows("release_line_register.csv")}
    subs = {r["SUBMISSION_ID"]: r for r in _csv_rows("submission_register.csv")}
    slines = _csv_rows("submission_line_register.csv")
    findings = _csv_rows("qc_findings_register.csv")

    # per-line stage rows
    per_line = {}
    for r in slines:
        per_line.setdefault(r["LINE_ID"], []).append(r)

    # scene-level TR/ED submissions (artifact path contains the scene name)
    scene_tr, scene_ed = {}, {}
    for sid, s in subs.items():
        if s["STAGE"] == "TR" and "/retrans/" in s.get("artifact_path", ""):
            m = re.search(r"/retrans/([^/]+)/", s["artifact_path"])
            if m:
                scene_tr[m.group(1)] = sid
        if s["STAGE"] == "ED" and "/retrans/" in s.get("artifact_path", ""):
            m = re.search(r"/retrans/([^/]+)/", s["artifact_path"])
            if m:
                scene_ed[m.group(1)] = sid

    RAW_SUB_BY_SURFACE = {
        "scenario": "SUB-RAW-002", "asset_pool": "SUB-RAW-002",
        "asset_field": "SUB-RAW-003", "dll": "SUB-RAW-001", "rule": "SUB-RAW-002",
    }

    units = {}   # unit_id -> dict
    line_index = {}

    def get_unit(unit_id, surface, name):
        if unit_id not in units:
            units[unit_id] = {"unit_id": unit_id, "surface": surface, "name": name,
                              "line_order": [], "lines": {}}
        return units[unit_id]

    for idx, lr in enumerate(lines):
        lid = lr["LINE_ID"]
        unit_id, surface, unit_name = unit_for_line(lr, file_map)
        u = get_unit(unit_id, surface, unit_name)
        rel = rels.get(lid, {})
        release_status = rel.get("RELEASE_STATUS", "")

        rows = per_line.get(lid, [])
        mtl_rows_all = sorted((r for r in rows if subs.get(r["SUBMISSION_ID"], {}).get("STAGE") == "MTL"), key=lambda r: _sub_num(r["SUBMISSION_ID"]))
        mtl_val = mtl_rows_all[-1]["value_text"] if mtl_rows_all else None
        tr_rows = sorted((r for r in rows if subs.get(r["SUBMISSION_ID"], {}).get("STAGE") == "TR"), key=lambda r: _sub_num(r["SUBMISSION_ID"]))
        ed_rows = sorted((r for r in rows if subs.get(r["SUBMISSION_ID"], {}).get("STAGE") == "ED"), key=lambda r: _sub_num(r["SUBMISSION_ID"]))
        tr_val = tr_rows[-1]["value_text"] if tr_rows else None
        # NOTE: no .strip() — trailing whitespace is part of the shipped value;
        # byte-exact parity with release_line_register.value_text is required.
        ed_final = lr.get("EN_FINAL") or None
        # register final wins over per-line rows (register == shipped catalog state);
        # divergence is surfaced as a provenance note, never silently.
        prov_note = ""
        if ed_rows and ed_final and ed_rows[-1]["value_text"] != ed_final:
            prov_note = (f"last ED row {ed_rows[-1]['SUBMISSION_ID']} ('{ed_rows[-1]['value_text'][:40]}') "
                        f"differs from register final; register value wins (matches catalog)")
        raw = lr.get("JP_TEXT") or ""

        # revision sequence for this line (chronological seed order)
        revs = []
        raw_sub = RAW_SUB_BY_SURFACE[surface]
        revs.append(("RAW", "raw", raw, raw_sub, 0))
        if mtl_val:
            mtls = [r for r in rows if subs.get(r["SUBMISSION_ID"], {}).get("STAGE") == "MTL"]
            revs.append(("MTL", "mtl", mtl_val, mtls[0]["SUBMISSION_ID"], 1))
        scene = lr.get("SCENARIO_ID") or ""
        tr_sid = scene_tr.get(scene) if surface in ("scenario", "asset_pool") and not tr_rows else None
        ed_sid = scene_ed.get(scene) if surface in ("scenario", "asset_pool") and ed_rows else None
        if tr_rows:
            revs.append(("TR", "tr", tr_val, tr_rows[-1]["SUBMISSION_ID"], 2))
        elif tr_sid:
            revs.append(("TR", "tr", None, tr_sid, 2))
        for r in ed_rows:
            revs.append(("ED", "ed", r["value_text"], r["SUBMISSION_ID"], 3))

        if release_status == "included" and rel.get("value_text"):
            revs.append(("FN", "fn", rel["value_text"], "SUB-FN-001", 9))

        stages = {
            "RAW": "done" if raw.strip() else "empty",
            "MTL": "done" if mtl_val else "none",
            "TR": ("done" if tr_rows else ("scene" if tr_sid else "pending")),
            "ED": "done" if (ed_final or ed_rows) else "pending",
            "QC": "none",
            "FN": {"included": "final", "untranslated_in_release": "shipped_jp",
                   "excluded_dead": "dead", "not_in_native_release": "excluded",
                   "n_a_empty_line": "n_a"}.get(release_status, "none"),
        }
        # tr/ed revision counters (position of the value within this line's seed revisions)
        tr_rev = None
        ed_rev = None
        for pos, entry in enumerate(revs, start=1):
            if entry[0] == "TR":
                tr_rev = pos
            if entry[0] == "ED":
                ed_rev = pos

        # QC state from findings
        open_f = [f["FINDING_ID"] for f in findings if f.get("LINE_ID") == lid and f.get("status") == "open"]
        any_f = [f["FINDING_ID"] for f in findings if f.get("LINE_ID") == lid]
        if open_f:
            qc_state = "attention"
        elif release_status == "included":
            qc_state = "passed"
        else:
            qc_state = "none"
        stages["QC"] = qc_state

        line = {
            "line_id": lid,
            "raw": raw,
            "mtl": mtl_val,
            "tr": tr_val,
            "ed": ed_final or (ed_rows[-1]["value_text"] if ed_rows else None),
            "provenance_note": prov_note,
            "speaker": None,
            "status": lr.get("STATUS", ""),
            "release_status": release_status,
            "release_note": rel.get("NOTES", ""),
            "rev": len(revs),
            "tr_rev": tr_rev,
            "ed_rev": ed_rev,
            "stages": stages,
            "qc": {"state": qc_state, "pinned_ed_rev": None, "open_findings": open_f},
            "stale": [],
            "ed_reviewed_tr_rev": None,
            "updated_at": (subs.get("SUB-FN-001", {}).get("date") or ""),
            "order": idx,
            "source": {
                "source_id": lr.get("SOURCE_ID", ""),
                "extraction_id": lr.get("EXTRACTION_ID", ""),
                "file_id": lr.get("FILE_ID", ""),
                "scenario_id": scene,
                "game_line_id": lr.get("GAME_LINE_ID", ""),
                "register_note": lr.get("NOTES", ""),
            },
        }
        u["lines"][lid] = line
        u["line_order"].append(lid)
        line_index[lid] = (unit_id, line)

    project = {
        "name": PROJECT_NAME,
        "game": "",
        "version": "",
        "created_at": now_iso(),
        "stages": STAGES,
        "seeded": {
            "registers_dir": str(REGISTERS_DIR),
            "catalog": (str(c) if (c := find_catalog()) else ""),
            "at": now_iso(),
            "note": ("App store is canonical after seed. Registers are frozen evidence of the "
                     "seed moment; regenerate them as exports after dashboard changes."),
        },
        "units": {},
    }
    # deterministic unit ordering: scenarios by scene, then pools, ast, dll, rule
    def unit_sort_key(uid):
        u = units[uid]
        if u["surface"] == "scenario":
            scene = u["name"]
            m = re.search(r"Lv(\d+)$", scene)
            num = int(m.group(1)) if m else (0 if scene in ("EVT_1_1",) else 50 if scene in ("Intro", "Legacy") else 99)
            return (0, num, scene)
        if u["surface"] == "asset_pool":
            return (1, 0, uid)
        if u["surface"] == "asset_field":
            return (2, 0, uid)
        if u["surface"] == "dll":
            return (3, 0, uid)
        return (4, 0, uid)

    ordered = sorted(units.keys(), key=unit_sort_key)
    for i, uid in enumerate(ordered):
        project["units"][uid] = {"surface": units[uid]["surface"], "name": units[uid]["name"], "order": i}

    # write seed revision history first (it also stamps seed_rev_count on lines),
    # then unit files, so stored counts and jsonl blocks always agree.
    _write_seed_revisions(units, per_line, subs)
    for uid, u in units.items():
        atomic_write_json(UNITS_DIR / unit_filename(uid), u)
    atomic_write_json(PROJECT_FILE, project)

    # issues seed from findings
    issues = {"next_issue_no": 1, "issues": {}}
    status_map = {"open": "reported", "recorded": "resolved", "accepted_by_design": "closed_accepted"}
    for f in findings:
        fid = f["FINDING_ID"]
        st = status_map.get(f.get("status", ""), "reported")
        issues["issues"][fid] = {
            "id": fid,
            "description": f.get("description", ""),
            "severity": f.get("SEVERITY", ""),
            "status": st,
            "line_id": f.get("LINE_ID") or None,
            "unit_id": line_index.get(f.get("LINE_ID"), (None,))[0] if f.get("LINE_ID") else None,
            "reported_by": f.get("REVIEWER", ""),
            "created_at": "",
            "updated_at": "",
            "history": [{"ts": "", "action": "seeded from qc_findings_register", "note": f"QC sub {f.get('QC_SUBMISSION_ID','')}", "by": "seed"}],
            "resolution_ref": f.get("RESOLUTION_SUBMISSION_ID", ""),
        }
    atomic_write_json(ISSUES_FILE, issues)
    atomic_write_json(IMPORTS_META_FILE, {"next_import_no": 1, "imports": {}})

    # seed submission records (history only)
    for sid, s in subs.items():
        if not (SUBMISSIONS_DIR / f"{sid}.json").exists():
            atomic_write_json(SUBMISSIONS_DIR / f"{sid}.json", {**s, "seeded": True})

    n_lines = len(line_index)
    print(f"seed complete: {len(units)} units, {n_lines} lines")
    by_surf = {}
    for uid, u in units.items():
        by_surf[u["surface"]] = by_surf.get(u["surface"], 0) + len(u["lines"])
    print("by surface:", by_surf)


def _write_seed_revisions(units, per_line, subs):
    """Write history/revisions/<unit>.jsonl reconstructed from registers."""
    RAW_SUB_BY_SURFACE = {
        "scenario": "SUB-RAW-002", "asset_pool": "SUB-RAW-002",
        "asset_field": "SUB-RAW-003", "dll": "SUB-RAW-001", "rule": "SUB-RAW-002",
    }
    for uid, u in units.items():
        path = unit_revisions_path(uid)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            for lid in u["line_order"]:
                line = u["lines"][lid]
                surface = u["surface"]
                scene = line.get("source", {}).get("scenario_id", "")
                rows = per_line.get(lid, [])
                entries = []

                def add(stage, field, value, sid, rev_no):
                    s = subs.get(sid, {})
                    entries.append({
                        "ts": s.get("date", ""), "actor": s.get("contributor_id", ""),
                        "stage": stage, "field": field, "value": value,
                        "sha10": sha10(value) if value else "",
                        "rev": rev_no, "submission_id": sid,
                        "note": ("scene-level (no per-line row)" if value is None and stage == "TR" else ""),
                    })

                add("RAW", "raw", line["raw"], RAW_SUB_BY_SURFACE[surface], 1)
                mtl_rows = sorted((r for r in rows if subs.get(r["SUBMISSION_ID"], {}).get("STAGE") == "MTL"), key=lambda r: _sub_num(r["SUBMISSION_ID"]))
                tr_rows = sorted((r for r in rows if subs.get(r["SUBMISSION_ID"], {}).get("STAGE") == "TR"), key=lambda r: _sub_num(r["SUBMISSION_ID"]))
                ed_rows = sorted((r for r in rows if subs.get(r["SUBMISSION_ID"], {}).get("STAGE") == "ED"), key=lambda r: _sub_num(r["SUBMISSION_ID"]))
                rev_no = 1
                if mtl_rows:
                    add("MTL", "mtl", mtl_rows[-1]["value_text"], mtl_rows[-1]["SUBMISSION_ID"], None)
                    rev_no += 1
                scene_tr = None
                for s in subs.values():
                    if s["STAGE"] == "TR" and "/retrans/" in s.get("artifact_path", ""):
                        m = re.search(r"/retrans/([^/]+)/", s["artifact_path"])
                        if m and m.group(1) == scene:
                            scene_tr = s["SUBMISSION_ID"]
                if tr_rows:
                    add("TR", "tr", tr_rows[-1]["value_text"], tr_rows[-1]["SUBMISSION_ID"], None)
                    rev_no += 1
                elif scene_tr:
                    add("TR", "tr", None, scene_tr, None)
                    rev_no += 1
                for r in ed_rows:
                    add("ED", "ed", r["value_text"], r["SUBMISSION_ID"], None)
                    rev_no += 1
                rel = line.get("release_status")
                if rel == "included" and line.get("ed"):
                    add("FN", "fn", line["ed"], "SUB-FN-001", None)
                    rev_no += 1
                # rev numbers are 1-based positions within this line's seed block
                for i, e in enumerate(entries):
                    e["rev"] = i + 1
                for e in entries:
                    f.write(json.dumps(e, ensure_ascii=False) + "\n")
                u["lines"][lid]["seed_rev_count"] = len(entries)


# --------------------------------------------------------------------------- imports

def scan_incoming(store):
    found = []
    for p in sorted(INCOMING_DIR.iterdir()):
        if p.is_file() and p.suffix.lower() in (".csv", ".tsv", ".json"):
            existing = None
            for imp in store.imports["imports"].values():
                if imp["filename"] == p.name:
                    existing = imp
                    break
            if not existing:
                no = store.imports["next_import_no"]
                iid = f"IMP-{no:03d}"
                store.imports["imports"][iid] = {
                    "id": iid, "filename": p.name, "format": p.suffix.lower().lstrip("."),
                    "received_at": now_iso(), "status": "pending", "error": "",
                    "rows_total": 0, "preview_counts": {}, "applied_as_sub": None,
                }
                store.imports["next_import_no"] = no + 1
                found.append(iid)
    if found:
        store.save_imports()
    return found


def import_preview(store, imp_id):
    imp = store.imports["imports"].get(imp_id)
    if not imp:
        return {"error": "import not found"}
    path = INCOMING_DIR / imp["filename"]
    if not path.exists():
        # maybe already moved; nothing to preview
        return {"error": f"file no longer in incoming/: {imp['filename']}"}
    from import_adapters import parse_any
    rows, errors = parse_any(path)
    imp["rows_total"] = len(rows)
    results = []
    counts = {"new_line": 0, "modified": 0, "unchanged": 0, "missing_id": 0, "invalid": 0}
    for row in rows:
        lid = (row.get("line_id") or "").strip()
        entry = {"row_no": row.get("_line_no"), "line_id": lid or None,
                 "match": None, "changes": {}, "effects": []}
        if lid and lid not in store.line_index:
            entry["match"] = "missing_id"
            counts["missing_id"] += 1
        elif not lid:
            # try to match by raw text
            raw = row.get("raw") or ""
            hit = _find_by_text(store, raw)
            if hit:
                entry["line_id"] = hit
                lid = hit
            else:
                entry["match"] = "invalid" if not (row.get("tr") or row.get("ed")) else "new_line"
                counts[entry["match"]] += 1
        if lid and lid in store.line_index and entry["match"] is None:
            unit_id, line = store.line_index[lid]
            changes = {}
            for k in ("raw", "mtl", "tr", "ed"):
                if row.get(k) is not None and row[k] != (line.get(k) or ""):
                    changes[k] = {"old": line.get(k) or "", "new": row[k]}
            if changes:
                entry["match"] = "modified"
                counts["modified"] += 1
                # workflow effects via a dry-run of the engine rules
                effs = []
                if "raw" in changes:
                    effs.append("RAW changed → TR/ED/QC/FN require reassessment")
                if "tr" in changes and (line.get("ed") or "").strip():
                    effs.append("TR changed → ED requires reconciliation; QC review stale")
                if "ed" in changes:
                    effs.append("ED changed → QC review required")
                if "mtl" in changes:
                    effs.append("MTL baseline updated (no downstream invalidation)")
                entry["effects"] = effs
            else:
                entry["match"] = "unchanged"
                counts["unchanged"] += 1
        results.append(entry)
    imp["preview_counts"] = counts
    store.save_imports()
    return {"import_id": imp_id, "rows_total": len(rows), "counts": counts,
            "errors": errors, "results": results}


def _find_by_text(store, text):
    if not (text or "").strip():
        return None
    nt = norm_text(text)
    for lid, (uid, line) in store.line_index.items():
        if norm_text(line.get("raw")) == nt:
            return lid
    return None


def import_apply(store, imp_id, actor="dashboard"):
    imp = store.imports["imports"].get(imp_id)
    if not imp:
        return {"error": "import not found"}
    preview = import_preview(store, imp_id)
    if preview.get("errors") and not preview.get("results"):
        imp["status"] = "rejected"
        imp["error"] = "; ".join(preview["errors"])
        store.save_imports()
        return {"error": imp["error"]}
    no = int(re.sub(r"\D", "", str(store.imports.get("next_sub_dash_no", 1))) or 1)
    sub_id = f"SUB-DASH-{no:03d}"
    applied, errors = [], []
    for r in preview["results"]:
        lid = r.get("line_id")
        if not lid or r["match"] in ("missing_id", "invalid", "unchanged"):
            continue
        row = next((x for x in _parse_rows_cached(imp) if x.get("_line_no") == r["row_no"]), {})
        fields = {k: v["new"] for k, v in r["changes"].items()}
        res = apply_line_change(store, lid, fields, actor=actor, note=sub_id)
        if res["status"] == "conflict":
            errors.append(f"{lid}: base revision conflict")
        else:
            applied.append(lid)
    if errors:
        # partial failure: roll back applied lines is out of scope for v1 —
        # instead reject the whole import before applying (see below). This path
        # only triggers if preview changed between preview and apply.
        imp["status"] = "rejected"
        imp["error"] = "conflicts at apply time: " + "; ".join(errors)
        store.save_imports()
        return {"error": imp["error"], "applied_before_conflict": applied}

    # record submission + transaction, move file
    atomic_write_json(SUBMISSIONS_DIR / f"{sub_id}.json", {
        "submission_id": sub_id, "stage": "TR+ED (dashboard import)",
        "date": now_iso(), "contributor_id": actor, "based_on": imp["id"],
        "artifact_path": f"imports/processed/{imp['filename']}",
        "checksum_sha256": hashlib.sha256((INCOMING_DIR / imp['filename']).read_bytes()).hexdigest()
            if (INCOMING_DIR / imp['filename']).exists() else "",
        "status": "accepted", "NOTES": f"import {imp['id']}; {len(applied)} lines applied",
    })
    shutil.move(str(INCOMING_DIR / imp["filename"]), str(PROCESSED_DIR / imp["filename"]))
    imp["status"] = "applied"
    imp["applied_as_sub"] = sub_id
    store.imports["next_sub_dash_no"] = no + 1
    store.save_imports()
    tx = STORE.record_transaction({
        "kind": "import", "actor": actor, "submission_id": sub_id,
        "unit_ids": sorted({store.line_index[l][0] for l in applied}),
        "line_count": len(applied), "effects_summary": f"import {imp['id']} applied via {sub_id}",
    })
    return {"status": "applied", "submission_id": sub_id, "lines_applied": len(applied),
            "tx_id": tx}


def _parse_rows_cached(imp):
    from import_adapters import parse_any
    rows, _ = parse_any(INCOMING_DIR / imp["filename"])
    return rows


def import_reject(store, imp_id, note=""):
    imp = store.imports["imports"].get(imp_id)
    if not imp:
        return {"error": "import not found"}
    path = INCOMING_DIR / imp["filename"]
    if path.exists():
        shutil.move(str(path), str(REJECTED_DIR / imp["filename"]))
    imp["status"] = "rejected"
    imp["error"] = note or "rejected by user"
    store.save_imports()
    return {"status": "rejected"}


# --------------------------------------------------------------------------- releases

def releases_view():
    out = {"catalog": None, "state_files": [], "patcher": None, "acceptance": None}
    cat_path = find_catalog()
    if cat_path and cat_path.exists():
        cat = read_json(cat_path)
        out["catalog"] = {
            "generated_at_utc": cat.get("generated_at_utc"),
            "dll_entries": len(cat.get("dll_entries", [])),
            "asset_entries": len(cat.get("asset_entries", [])),
            "changed_data_files": len(cat.get("changed_data_files", [])),
        }
    for p in sorted(STATE_DIR.glob("*.json")) if STATE_DIR.exists() else []:
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        out["state_files"].append({"name": p.name, "sha256": h, "size": p.stat().st_size})
    pty = PATCHER_DIR / "patcher.py" if PATCHER_DIR.exists() else None
    if pty and pty.exists():
        out["patcher"] = {"path": str(PTY) if False else str(pty), "sha256": hashlib.sha256(pty.read_bytes()).hexdigest()}
    last = read_json(RELEASES_DIR / "acceptance_last.json")
    if last:
        out["acceptance"] = last
    return out


def run_acceptance():
    if not ACCEPTANCE_SCRIPT.exists():
        return {"error": f"acceptance script not found: {ACCEPTANCE_SCRIPT}"}
    proc = subprocess.run(
        [sys.executable, str(ACCEPTANCE_SCRIPT)], cwd=str(WS_ROOT),
        capture_output=True, text=True, timeout=600,
        encoding="utf-8", errors="replace")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = RELEASES_DIR / f"acceptance_{ts}.log"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(proc.stdout or "")
        if proc.stderr:
            f.write("\n--- stderr ---\n" + proc.stderr)
    tail = (proc.stdout or "").strip().splitlines()[-25:]
    result = {"ts": now_iso(), "exit_code": proc.returncode, "tail": tail,
              "log": str(log_path)}
    atomic_write_json(RELEASES_DIR / "acceptance_last.json", result)
    return result


# --------------------------------------------------------------------------- http

class Handler(BaseHTTPRequestHandler):
    server_version = "i8n-dash/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

    def _send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, ctype):
        if not path.exists():
            self.send_error(404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        try:
            return json.loads(raw.decode("utf-8")) if raw else {}
        except json.JSONDecodeError:
            return {"__error__": "invalid JSON body"}

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", ""):
            return self._send_file(FRONTEND_DIR / "index.html", "text/html; charset=utf-8")
        if path in ("/styles.css", "/app.js"):
            return self._send_file(FRONTEND_DIR / path.lstrip("/"),
                                   "text/css" if path.endswith(".css") else "application/javascript; charset=utf-8")
        if not path.startswith("/api/"):
            self.send_error(404)
            return
        try:
            self.route_get(path)
        except Exception as e:
            import traceback
            self._send_json({"error": str(e), "trace": traceback.format_exc()[-800:]}, 500)

    def route_get(self, path):
        from urllib.parse import unquote
        path = unquote(path)
        if path == "/api/health":
            return self._send_json({"ok": True, "ts": now_iso()})
        if path == "/api/project":
            return self._send_json(self.project_overview())
        if path == "/api/units":
            return self._send_json(self.units_list())
        if path == "/api/lines":
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            cat = (qs.get("cat") or [""])[0]
            unit = (qs.get("unit") or [""])[0]
            rows = []
            for uid, meta in sorted(STORE.project["units"].items(), key=lambda kv: kv[1]["order"]):
                u = STORE.units.get(uid)
                if not u:
                    continue
                if unit and uid != unit:
                    continue
                for lid in u["line_order"]:
                    line = u["lines"][lid]
                    c, detail = derived_state(line)
                    if cat and c != cat:
                        continue
                    rows.append({
                        "line_id": lid, "unit_id": uid, "unit_name": u["name"],
                        "state_cat": c, "detail": detail,
                        "raw": (line.get("raw") or "")[:100],
                        "ed": ((line.get("ed") or line.get("tr")) or "")[:100],
                    })
            return self._send_json({"lines": rows})
        m = re.match(r"^/api/unit/([^/]+)$", path)
        if m:
            uid = m.group(1)
            u = STORE.units.get(uid)
            if not u:
                return self._send_json({"error": "unit not found"}, 404)
            slim = {
                "unit_id": uid, "surface": u["surface"], "name": u["name"],
                "lines": [
                    {
                        "line_id": lid, "raw": l.get("raw"), "mtl": l.get("mtl"),
                        "tr": l.get("tr"), "ed": l.get("ed"), "status": l.get("status"),
                        "release_status": l.get("release_status"), "stages": l.get("stages"),
                        "stale": l.get("stale", []), "rev": l.get("rev"),
                        "qc_state": l.get("qc", {}).get("state"),
                        "open_findings": len(l.get("qc", {}).get("open_findings", [])),
                        "state_cat": derived_state(l)[0],
                    } for lid, l in ((x, u["lines"][x]) for x in u["line_order"])
                ],
            }
            return self._send_json(slim)
        m = re.match(r"^/api/line/([^/]+)$", path)
        if m:
            return self.line_detail(m.group(1))
        if path == "/api/search":
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query).get("q", [""])[0]
            limit = int(parse_qs(urlparse(self.path).query).get("limit", ["25"])[0])
            return self._send_json(self.search(q, limit))
        if path == "/api/issues":
            return self._send_json({"issues": list(STORE.issues["issues"].values())})
        m = re.match(r"^/api/issues/([^/]+)$", path)
        if m:
            iss = STORE.issues["issues"].get(m.group(1))
            return self._send_json(iss or {"error": "not found"}, 200 if iss else 404)
        if path == "/api/imports":
            return self._send_json({"imports": list(STORE.imports["imports"].values())})
        m = re.match(r"^/api/imports/([^/]+)/preview$", path)
        if m:
            with LOCK:
                return self._send_json(import_preview(STORE, m.group(1)))
        if path == "/api/releases":
            return self._send_json(releases_view())
        if path == "/api/transactions":
            return self._send_json({"transactions": STORE.recent_transactions()})
        self._send_json({"error": "unknown endpoint"}, 404)

    def line_detail(self, lid):
        hit = STORE.line_index.get(lid)
        if not hit:
            return self._send_json({"error": "line not found"}, 404)
        uid, line = hit
        unit = STORE.units[uid]
        # revisions: seed block (positional, from stored counts) + post-seed entries (by line_id)
        revs = []
        path = unit_revisions_path(uid)
        if path.exists():
            with open(path, "r", encoding="utf-8-sig") as f:
                allrevs = [json.loads(l) for l in f if l.strip()]
            pos = 0
            for other_lid in unit["line_order"]:
                if other_lid == lid:
                    break
                pos += unit["lines"][other_lid].get("seed_rev_count", _count_seed_revisions_for(unit, other_lid))
            mine_n = line.get("seed_rev_count", _count_seed_revisions_for(unit, lid))
            if len(allrevs) >= pos + mine_n:
                revs = allrevs[pos:pos + mine_n]
            revs += [e for e in allrevs if e.get("line_id") == lid]
        # context lines
        idx = unit["line_order"].index(lid)
        prev_lid = unit["line_order"][idx - 1] if idx > 0 else None
        next_lid = unit["line_order"][idx + 1] if idx + 1 < len(unit["line_order"]) else None
        issues = [i for i in STORE.issues["issues"].values() if i.get("line_id") == lid]
        self._send_json({
            "unit_id": uid, "unit_name": unit["name"], "surface": unit["surface"],
            "line": line, "state_cat": derived_state(line), 
            "revisions": revs, "issues": issues,
            "context": {"prev": unit["lines"][prev_lid] if prev_lid else None,
                        "next": unit["lines"][next_lid] if next_lid else None},
        })

    def do_POST(self):
        from urllib.parse import unquote
        path = unquote(self.path.split("?")[0])
        body = self._body()
        if "__error__" in body:
            return self._send_json({"error": body["__error__"]}, 400)
        try:
            with LOCK:
                self.route_post(path, body)
        except Exception as e:
            import traceback
            self._send_json({"error": str(e), "trace": traceback.format_exc()[-800:]}, 500)

    def route_post(self, path, body):
        m = re.match(r"^/api/line/([^/]+)$", path)
        if m:
            lid = m.group(1)
            actor = body.get("actor", "dashboard-user")
            res = apply_line_change(STORE, lid, body, actor=actor,
                                    note=body.get("note", ""), base_rev=body.get("base_rev"))
            if res["status"] == "applied":
                STORE.record_transaction({
                    "kind": "edit", "actor": actor, "line_count": 1,
                    "unit_ids": [STORE.line_index[lid][0]],
                    "effects_summary": "; ".join(res.get("effects", [])),
                    "submission_id": body.get("note"),
                })
            return self._send_json(res, 200 if res["status"] != "conflict" else 409)
        if path == "/api/qc":
            res = qc_action(STORE, body.get("line_id", ""), body.get("verdict", ""),
                            actor=body.get("actor", "dashboard-user"), note=body.get("note", ""))
            return self._send_json(res, 200 if res["status"] == "applied" else 400)
        if path == "/api/agent/submit":
            lines = body.get("lines", [])
            actor = body.get("actor", "agent")
            out = {"applied": [], "noop": [], "conflicts": [], "not_found": []}
            for item in lines:
                lid = item.get("line_id")
                fields = {k: item.get(k) for k in ("raw", "mtl", "tr", "ed") if k in item}
                res = apply_line_change(STORE, lid, fields, actor=actor,
                                        note=body.get("note", ""), base_rev=item.get("base_rev"))
                out[{"applied": "applied", "noop": "noop", "conflict": "conflicts",
                     "not_found": "not_found"}[res["status"]] if res["status"] in ("applied", "noop", "conflict", "not_found") else "noop"].append(
                    lid if isinstance(res.get("line_id"), str) and not res.get("changes") else {**{k: v for k, v in res.items()}})
            applied_ids = [x if isinstance(x, str) else x.get("line_id") for x in out["applied"]]
            if applied_ids:
                STORE.record_transaction({
                    "kind": "agent", "actor": actor, "line_count": len(applied_ids),
                    "unit_ids": sorted({STORE.line_index[l][0] for l in applied_ids if l}),
                    "effects_summary": f"agent submission: {len(applied_ids)} lines",
                })
            return self._send_json(out)
        if path == "/api/issues":
            desc = (body.get("description") or "").strip()
            if not desc:
                return self._send_json({"error": "description required"}, 400)
            no = STORE.issues["next_issue_no"]
            iid = f"ISS-{no:03d}"
            STORE.issues["issues"][iid] = {
                "id": iid, "description": desc, "severity": body.get("severity", ""),
                "status": "reported", "line_id": body.get("line_id"),
                "unit_id": (STORE.line_index[body["line_id"]][0] if body.get("line_id") in STORE.line_index else None),
                "reported_by": body.get("actor", "dashboard-user"),
                "created_at": now_iso(), "updated_at": now_iso(),
                "history": [{"ts": now_iso(), "action": "reported", "note": "", "by": body.get("actor", "dashboard-user")}],
                "resolution_ref": "",
            }
            STORE.issues["next_issue_no"] = no + 1
            STORE.save_issues()
            return self._send_json({"id": iid}, 201)
        m = re.match(r"^/api/issues/([^/]+)/status$", path)
        if m:
            iss = STORE.issues["issues"].get(m.group(1))
            if not iss:
                return self._send_json({"error": "not found"}, 404)
            new_status = body.get("status", "")
            allowed = {"reported", "triaged", "assigned", "correction_required",
                       "verification", "resolved", "closed_invalid", "closed_duplicate",
                       "closed_accepted"}
            if new_status not in allowed:
                return self._send_json({"error": f"bad status (allowed: {sorted(allowed)})"}, 400)
            iss["status"] = new_status
            iss["updated_at"] = now_iso()
            iss["history"].append({"ts": now_iso(), "action": f"status→{new_status}",
                                   "note": body.get("reason", ""), "by": body.get("actor", "dashboard-user")})
            STORE.save_issues()
            return self._send_json({"ok": True})
        m = re.match(r"^/api/issues/([^/]+)/link$", path)
        if m:
            iss = STORE.issues["issues"].get(m.group(1))
            if not iss:
                return self._send_json({"error": "not found"}, 404)
            lid = body.get("line_id")
            if lid and lid in STORE.line_index:
                iss["line_id"] = lid
                iss["unit_id"] = STORE.line_index[lid][0]
                iss["history"].append({"ts": now_iso(), "action": f"linked→{lid}", "note": "", "by": body.get("actor", "")})
                STORE.save_issues()
                return self._send_json({"ok": True})
            return self._send_json({"error": "line not found"}, 400)
        if path == "/api/imports/scan":
            found = scan_incoming(STORE)
            return self._send_json({"found": found})
        m = re.match(r"^/api/imports/([^/]+)/apply$", path)
        if m:
            res = import_apply(STORE, m.group(1), actor=body.get("actor", "dashboard-user"))
            return self._send_json(res, 200 if res.get("status") == "applied" else 400)
        m = re.match(r"^/api/imports/([^/]+)/reject$", path)
        if m:
            res = import_reject(STORE, m.group(1), note=body.get("note", ""))
            return self._send_json(res)
        if path == "/api/releases/run_acceptance":
            res = run_acceptance()
            return self._send_json(res, 200 if "error" not in res else 500)
        self._send_json({"error": "unknown endpoint"}, 404)

    # ---- computed views -----------------------------------------------------

    def project_overview(self):
        cats = {c: [] for c in ATTENTION_ORDER}
        cats["final"], cats["empty"], cats["out_of_scope"] = [], [], []
        reasons = {c: {} for c in ATTENTION_ORDER}
        units_summary = {}
        total_lines = 0
        content_lines = 0
        stage_counts = {"RAW": 0, "MTL": 0, "TR": 0, "ED": 0, "QC": 0, "FN": 0}
        scope = {"in_scope": 0, "oos": 0, "dead_excluded": 0}
        oos_by_status = {}
        stage_counts_in_scope = dict(stage_counts)
        for uid, u in STORE.units.items():
            ucats = {c: 0 for c in ATTENTION_ORDER + ["final", "empty", "out_of_scope"]}
            open_issues_u = 0
            last_upd = ""
            for lid, line in u["lines"].items():
                cat, detail = derived_state(line)
                ucats[cat] = ucats.get(cat, 0) + 1
                cats.setdefault(cat, []).append({"line_id": lid, "unit_id": uid, "detail": detail})
                rel = line.get("release_status", "")
                if (line.get("raw") or "").strip():
                    content_lines += 1
                    if rel == "included":
                        scope["in_scope"] += 1
                    elif rel == "excluded_dead":
                        scope["dead_excluded"] += 1
                    else:
                        scope["oos"] += 1
                        oos_by_status[rel or "unknown"] = oos_by_status.get(rel or "unknown", 0) + 1
                if cat == "needs_revision":
                    if line.get("stale"):
                        k = "stale:" + "+".join(line["stale"])
                        reasons[cat][k] = reasons[cat].get(k, 0) + 1
                    if line.get("qc", {}).get("open_findings"):
                        reasons[cat]["open findings"] = reasons[cat].get("open findings", 0) + 1
                if line.get("updated_at", "") > last_upd:
                    last_upd = line["updated_at"]
            for i in STORE.issues["issues"].values():
                if i.get("unit_id") == uid and i["status"] not in ("resolved", "closed_invalid", "closed_duplicate", "closed_accepted"):
                    open_issues_u += 1
            units_summary[uid] = {"cats": ucats, "open_issues": open_issues_u, "last_updated": last_upd}
            total_lines += len(u["lines"])
        for uid, u in STORE.units.items():
            for line in u["lines"].values():
                in_scope = line.get("release_status") == "included" and bool((line.get("raw") or "").strip())
                for s in STAGES:
                    if line["stages"].get(s) in ("done", "scene", "final", "passed"):
                        stage_counts[s] += 1
                        if in_scope:
                            stage_counts_in_scope[s] += 1
        open_issues = [i for i in STORE.issues["issues"].values()
                       if i["status"] not in ("resolved", "closed_invalid", "closed_duplicate", "closed_accepted")]
        return {
            "project": STORE.project,
            "total_units": len(STORE.units),
            "total_lines": total_lines,
            "total_content_lines": content_lines,
            "stage_counts": stage_counts,
            "scope": scope,
            "oos_by_status": oos_by_status,
            "stage_counts_in_scope": stage_counts_in_scope,
            "attention_reasons": {c: sorted(v.items(), key=lambda kv: (-kv[1], kv[0])) for c, v in reasons.items()},
            "attention": {k: v[:200] for k, v in cats.items()},
            "attention_counts": {k: len(v) for k, v in cats.items()},
            "open_issues": open_issues,
            "recent_transactions": STORE.recent_transactions(),
        }

    def units_list(self):
        out = []
        for uid, meta in STORE.project["units"].items():
            u = STORE.units[uid]
            ucats = {c: 0 for c in ATTENTION_ORDER + ["final", "empty", "out_of_scope"]}
            open_issues = 0
            last_upd = ""
            for line in u["lines"].values():
                cat, _ = derived_state(line)
                ucats[cat] = ucats.get(cat, 0) + 1
                if line.get("updated_at", "") > last_upd:
                    last_upd = line["updated_at"]
            for i in STORE.issues["issues"].values():
                if i.get("unit_id") == uid and i["status"] not in ("resolved", "closed_invalid", "closed_duplicate", "closed_accepted"):
                    open_issues += 1
            out.append({
                "unit_id": uid, "name": meta["name"], "surface": meta["surface"],
                "order": meta["order"], "lines": len(u["lines"]),
                "cats": ucats, "open_issues": open_issues, "last_updated": last_upd,
            })
        out.sort(key=lambda x: x["order"])
        return {"units": out}

    def search(self, q, limit=25):
        nq = norm_text(q)
        if not nq:
            return []
        results = []
        for lid, (uid, line) in STORE.line_index.items():
            hit_fields = []
            for field in ("raw", "tr", "ed", "mtl"):
                v = line.get(field) or ""
                if nq in norm_text(v):
                    hit_fields.append(field)
            if hit_fields:
                results.append({
                    "line_id": lid, "unit_id": uid,
                    "unit_name": STORE.units[uid]["name"],
                    "matched_fields": hit_fields,
                    "raw": (line.get("raw") or "")[:80],
                    "tr": (line.get("tr") or "")[:80],
                    "ed": (line.get("ed") or "")[:80],
                })
            if len(results) >= limit * 4:
                break
        # rank: raw hits first, then tr, ed
        rank = {"raw": 0, "tr": 1, "ed": 2, "mtl": 3}
        results.sort(key=lambda r: min(rank[f] for f in r["matched_fields"]))
        return results[:limit]


def _count_seed_revisions_for(unit, lid):
    """Number of seed revision entries a line contributes (must mirror seed logic)."""
    n = 1  # RAW
    line = unit["lines"][lid]
    if (line.get("mtl") or ""):
        n += 1
    if line["stages"]["TR"] in ("done", "scene"):
        n += 1
    # ED rows: per-line ED rows are not stored on the line; seed wrote one entry
    # per stage-map row plus none for scene-era. We stored ed_rev count proxy:
    # use rev arithmetic: total rev - RAW - MTL - TR - FN(included)
    fn = 1 if line.get("release_status") == "included" and (line.get("ed") or "") else 0
    tr_part = 1 if line["stages"]["TR"] in ("done", "scene") else 0
    mtl_part = 1 if (line.get("mtl") or "") else 0
    ed_count = max(0, line["rev"] - 1 - mtl_part - tr_part - fn)
    return n + ed_count


def main():
    global STORE
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=PORT_DEFAULT)
    ap.add_argument("--seed", action="store_true")
    ap.add_argument("--reseed", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="start even if something already answers on the port")
    args = ap.parse_args()

    if args.seed or args.reseed:
        if args.reseed and PROJECT_FILE.exists():
            for p in UNITS_DIR.glob("*.json"):
                p.unlink()
            for p in REVISIONS_DIR.glob("*.jsonl"):
                p.unlink()
            for name in (PROJECT_FILE, ISSUES_FILE, IMPORTS_META_FILE):
                if name.exists():
                    name.unlink()
        seed_project()
        return

    STORE = Store().load()
    # integrity: verify project.units keys == unit files
    files = {p.name for p in UNITS_DIR.glob("*.json")}
    want = {unit_filename(u) for u in STORE.project.get("units", {})}
    if files != want:
        print(f"WARNING: unit file mismatch: missing={want - files}, extra={files - want}")
    if not args.force:
        import urllib.request as _ur
        import urllib.error as _ue
        try:
            with _ur.urlopen(f"http://{HOST}:{args.port}/api/health", timeout=1.0) as r:
                probe = r.getcode()
        except _ue.HTTPError:
            probe = True  # an HTTP server answered, just not /api/health
        except Exception:
            probe = None
        if probe is not None:
            print(f"ERROR: port {args.port} already serving. "
                  f"Kill the stale process or pass --force to shadow it.")
            return 2
    httpd = ThreadingHTTPServer((HOST, args.port), Handler)
    print(f"dashboard: http://{HOST}:{args.port}  ({len(STORE.line_index)} lines / {len(STORE.units)} units)")
    print("Ctrl+C to stop. Loopback-only; no auth.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    raise SystemExit(main())
