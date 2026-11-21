/* Translation project dashboard — frontend (vanilla JS, no build step). */
"use strict";

const $ = (sel, el = document) => el.querySelector(sel);
const $$ = (sel, el = document) => Array.from(el.querySelectorAll(sel));
const main = $("#main");

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
async function api(path, opts) {
  const r = await fetch("/api" + path, opts);
  let body = null;
  try { body = await r.json(); } catch (e) { /* non-json */ }
  if (!r.ok) throw new Error((body && body.error) || `HTTP ${r.status}`);
  return body;
}
const POST = path => (body) => api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });

const CAT_LABELS = {
  needs_revision: "Needs revision", awaiting_translation: "Awaiting translation",
  awaiting_edit: "Awaiting edit", awaiting_qc: "Awaiting QC",
  final: "Final", empty: "Empty line", out_of_scope: "Out of scope (kept JP)",
};

function stageChain(stages, stale) {
  const order = ["RAW", "MTL", "TR", "ED", "QC", "FN"];
  return `<div class="stagechain">` + order.map(s => {
    const v = stages[s] || "none";
    const st = (stale || []).includes(s) ? "stale" : v;
    return `<span class="stagelink ${st}" title="${esc(v)}">${s}</span>` + (s !== "FN" ? `<span class="arrow">→</span>` : "");
  }).join("") + `</div>`;
}

function lineRow(l) {
  const cat = l.state_cat || "out_of_scope";
  return `<tr data-lid="${esc(l.line_id)}" data-v-lid="${esc(l.line_id)}" data-v-state="${cat}" style="cursor:pointer">
    <td class="mono">${esc(l.line_id)}</td>
    <td>${esc((l.raw || "").slice(0, 40))}${(l.raw || "").length > 40 ? "…" : ""}</td>
    <td>${esc((l.tr || l.ed || "").slice(0, 50))}</td>
    <td><span class="pill ${cat}">${CAT_LABELS[cat]}</span></td>
    <td class="stagecell">${stageChain(l.stages || {}, l.stale)}</td>
  </tr>`;
}

/* ------------------------------------------------------------------ project */
async function viewProject() {
  const p = await api("/project");
  document.title = `${p.project.name} — Translation Dashboard`;
  const bn = document.getElementById("brandname");
  if (bn) bn.textContent = p.project.name;
  const cats = p.attention_counts || {};
  const scope = p.scope || {};
  const inScope = scope.in_scope != null ? scope.in_scope : (cats.final || 0);
  const finalN = cats.final || 0;
  const pct = inScope ? Math.round((finalN / inScope) * 1000) / 10 : 0;
  const content = p.total_content_lines != null ? p.total_content_lines : 0;
  const stages = p.stage_counts_in_scope || {};
  const stageOrder = ["RAW", "MTL", "TR", "ED", "QC", "FN"];
  const stageTags = { MTL: "optional machine baseline", TR: "incl. scene-level rows" };
  const attCats = ["needs_revision", "awaiting_translation", "awaiting_edit", "awaiting_qc"];
  const allClear = attCats.every(c => !(cats[c] || 0));
  const oosParts = Object.entries(p.oos_by_status || {}).map(([k, v]) => `${k.replace(/_/g, " ")} ${v.toLocaleString()}`).join(" · ");
  main.innerHTML = `
    <h1>${esc(p.project.name)}</h1>
    <div class="card hero">
      <div class="hero-top">
        <div><span class="hero-num">${finalN.toLocaleString()}</span><span class="hero-den"> / ${inScope.toLocaleString()}</span></div>
        <div class="hero-pct">${pct}%</div>
      </div>
      <div class="bar hero-bar"><div style="width:${Math.min(pct, 100)}%;background:var(--ok)"></div></div>
      <div class="lbl">final — in-scope content lines (release-included)</div>
    </div>
    <h2>Attention required</h2>
    ${allClear ? `<div class="okmsg">All clear — no lines need attention.</div>` : attCats.map(c => `
      <div style="margin:8px 0">
        <a href="#/lines?cat=${c}" class="pill ${c}">${CAT_LABELS[c]}: ${cats[c] || 0}</a>
        ${(p.attention_reasons || {})[c]?.length ? `<span class="note"> — ${(p.attention_reasons[c]).slice(0, 3).map(([r, n]) => `${esc(r)} ×${n}`).join(" · ")}</span>` : ""}
        <div id="att-${c}" class="muted" style="font-size:12px;margin-top:4px"></div>
      </div>`).join("")}
    <h2>Pipeline <span class="note">in-scope lines</span></h2>
    <div class="stage-rows">
      ${stageOrder.map(s => { const n = stages[s] || 0; const pp = inScope ? Math.round((n / inScope) * 1000) / 10 : 0; return `
        <div class="srow">
          <span class="sname">${s}</span>
          <div class="sbar"><div style="width:${Math.min(pp, 100)}%"></div></div>
          <span class="sval mono">${n.toLocaleString()} / ${inScope.toLocaleString()}</span>
          <span class="spct">${pp}%</span>
          ${stageTags[s] ? `<span class="stagetag">${stageTags[s]}</span>` : ""}
        </div>`; }).join("")}
    </div>
    <p class="note">Out-of-scope lines stop at triage by design. RAW extraction covered all ${content.toLocaleString()} text lines, including out-of-scope.</p>
    <h2>Open issues</h2>
    <div>${(p.open_issues || []).length ? `<span class="pill needs_revision">${(p.open_issues || []).length} open</span>` : '<span class="okmsg">none</span>'}</div>
    <h2>Recent transactions</h2>
    <ul class="txlist">${(p.recent_transactions || []).map(t => `<li><b>${esc(t.tx_id)}</b> · ${esc(t.kind)} · ${t.line_count} line(s) · ${esc(t.effects_summary || "")}<div class="note">${esc(t.ts || "")} by ${esc(t.actor || "")}</div></li>`).join("") || '<li class="muted">none yet</li>'}</ul>
    <div class="oos-note">Out of scope, triaged terminal (no translation required): <b>${(scope.oos || 0).toLocaleString()}</b>${oosParts ? ` — ${oosParts}` : ""} · <a href="#/lines?cat=out_of_scope">view / re-triage</a>${scope.dead_excluded ? `<span class="muted"> · ${scope.dead_excluded} dead lines excluded from totals</span>` : ""}</div>
  `;
  // fill attention samples lazily
  for (const c of attCats) {
    const el = $(`#att-${c}`);
    if (!el) continue;
    const items = (p.attention[c] || []).slice(0, 5);
    if (items.length) el.innerHTML = items.map(i => `<a href="#/line/${esc(i.line_id)}">${esc(i.line_id)}</a> <span class="note">${esc(i.detail || "")}</span>`).join("<br>");
  }
}

/* ------------------------------------------------------------------- units */
async function viewUnits() {
  const u = await api("/units");
  main.innerHTML = `<h1>Units (files / scenes)</h1>
    <p class="note">Click a column header to sort. Lines counts content lines; empty rows are shown in parentheses.</p>
    <table id="units-table"><thead><tr>
      <th data-sort="unit">Unit</th><th data-sort="surface">Surface</th>
      <th data-sort="lines" data-num="1">Lines</th><th data-sort="final" data-num="1">Final</th>
      <th data-sort="tl" data-num="1">Awaiting TL</th><th data-sort="ed" data-num="1">Awaiting ED</th>
      <th data-sort="qc" data-num="1">Awaiting QC</th><th data-sort="rev" data-num="1">Needs rev</th>
      <th data-sort="issues" data-num="1">Open issues</th>
    </tr></thead>
    <tbody>${u.units.map(x => {
      const emptyN = x.cats.empty || 0;
      const content = Math.max(0, (x.lines || 0) - emptyN);
      return `
      <tr data-uid="${esc(x.unit_id)}" style="cursor:pointer"
          data-v-unit="${esc(x.name)}" data-v-surface="${esc(x.surface)}" data-v-lines="${content}"
          data-v-final="${x.cats.final || 0}" data-v-tl="${x.cats.awaiting_translation || 0}"
          data-v-ed="${x.cats.awaiting_edit || 0}" data-v-qc="${x.cats.awaiting_qc || 0}"
          data-v-rev="${x.cats.needs_revision || 0}" data-v-issues="${x.open_issues || 0}">
        <td class="mono">${esc(x.name)}</td><td>${esc(x.surface)}</td>
        <td>${content}${emptyN ? ` <span class="muted small">(${emptyN} empty)</span>` : ""}</td>
        <td>${x.cats.final || 0}</td><td>${x.cats.awaiting_translation || 0}</td>
        <td>${x.cats.awaiting_edit || 0}</td><td>${x.cats.awaiting_qc || 0}</td>
        <td class="${(x.cats.needs_revision || 0) ? "errmsg" : ""}">${x.cats.needs_revision || 0}</td>
        <td class="${x.open_issues ? "errmsg" : ""}">${x.open_issues}</td>
      </tr>`;
    }).join("")}
    </tbody></table>`;
  $$("#main tr[data-uid]").forEach(tr => tr.onclick = () => location.hash = `#/unit/${tr.dataset.uid}`);
  makeSortable($("#units-table"));
}

/* ------------------------------------------------------------------ unit */
async function viewUnit(uid) {
  const u = await api("/unit/" + encodeURIComponent(uid));
  const cats = {};
  u.lines.forEach(l => cats[l.state_cat] = (cats[l.state_cat] || 0) + 1);
  const emptyN = u.lines.filter(l => !(l.raw || "").trim()).length;
  const contentN = u.lines.length - emptyN;
  main.innerHTML = `
    <a href="#/units" class="note">← units</a>
    <h1>${esc(u.name)} <span class="muted mono">${esc(uid)}</span> <span class="muted">${contentN} lines${emptyN ? ` (+${emptyN} empty)` : ""}</span></h1>
    ${stageChain({}, [])}
    <div class="filterbar">
      <select id="fcat"><option value="">all states (${u.lines.length})</option>
        ${Object.entries(cats).map(([k, n]) => `<option value="${k}">${CAT_LABELS[k]} (${n})</option>`).join("")}
      </select>
      <input type="text" id="fsearch" placeholder="filter text…">
      ${emptyN ? `<label class="muted" style="display:flex;align-items:center;gap:4px"><input type="checkbox" id="fnoempty" checked> hide empty (${emptyN})</label>` : ""}
    </div>
    <table id="unitlines-table"><thead><tr><th data-sort="lid">Line ID</th><th>JP</th><th>EN (TR/ED)</th><th data-sort="state">State</th><th>Stages</th></tr></thead>
    <tbody id="unitlines"></tbody></table>`;
  const tbody = $("#unitlines");
  function render(lines) {
    tbody.innerHTML = lines.slice(0, 500).map(lineRow).join("") + (lines.length > 500 ? `<tr><td colspan=5 class="note">… ${lines.length - 500} more (use filter)</td></tr>` : "");
    $$("#unitlines tr[data-lid]").forEach(tr => tr.onclick = () => location.hash = `#/line/${tr.dataset.lid}`);
  }
  function applyFilter() {
    const cat = $("#fcat").value, q = $("#fsearch").value.trim().toLowerCase();
    let lines = u.lines;
    if ($("#fnoempty") && $("#fnoempty").checked) lines = lines.filter(l => l.state_cat !== "empty");
    if (cat) lines = lines.filter(l => l.state_cat === cat);
    if (q) lines = lines.filter(l => [l.raw, l.tr, l.ed].some(v => (v || "").toLowerCase().includes(q)));
    render(lines);
  }
  $("#fcat").onchange = applyFilter;
  $("#fsearch").oninput = applyFilter;
  if ($("#fnoempty")) $("#fnoempty").onchange = applyFilter;
  makeSortable($("#unitlines-table"));
  applyFilter();
}

/* --------------------------------------------------------------- lines */
async function viewLines() {
  const q = new URLSearchParams((location.hash.split("?")[1] || ""));
  const cat = q.get("cat") || "";
  const d = await api("/lines?cat=" + encodeURIComponent(cat));
  const lines = d.lines || [];
  main.innerHTML = `
    <a href="#/project" class="note">← project</a>
    <h1>${cat ? CAT_LABELS[cat] : "Lines"} — ${lines.length} line(s)</h1>
    <table id="lines-table"><thead><tr>
      <th data-sort="lid">Line ID</th><th data-sort="unit">Unit</th>
      <th data-sort="why">Why</th><th>JP</th><th>EN (TR/ED)</th>
    </tr></thead>
    <tbody>${lines.map(x => `
      <tr data-lid="${esc(x.line_id)}" style="cursor:pointer"
          data-v-lid="${esc(x.line_id)}" data-v-unit="${esc(x.unit_name)}" data-v-why="${esc(x.detail || "")}">
        <td class="mono">${esc(x.line_id)}</td>
        <td class="mono note">${esc(x.unit_name)}</td>
        <td>${esc(x.detail || CAT_LABELS[x.state_cat] || "")}</td>
        <td>${esc((x.raw || "").slice(0, 60))}</td>
        <td>${esc((x.ed || "").slice(0, 60))}</td>
      </tr>`).join("")}
    </tbody></table>`;
  $$("#lines-table tr[data-lid]").forEach(tr => tr.onclick = () => location.hash = `#/line/${tr.dataset.lid}`);
  makeSortable($("#lines-table"));
}

function makeSortable(table) {
  const ths = $$("thead th[data-sort]", table);
  if (!ths.length) return;
  let cur = null, dir = 1;
  const tbody = $("tbody", table);
  const dv = (tr, k) => tr.dataset["v" + k[0].toUpperCase() + k.slice(1)] ?? "";
  ths.forEach(th => {
    th.classList.add("sortable");
    th.addEventListener("click", () => {
      const k = th.dataset.sort;
      if (cur === k) dir *= -1; else { cur = k; dir = 1; }
      ths.forEach(t => t.classList.remove("sorted-asc", "sorted-desc"));
      th.classList.add(dir === 1 ? "sorted-asc" : "sorted-desc");
      const num = th.dataset.num === "1";
      const all = Array.from(tbody.children);
      all.sort((a, b) => {
        const av = dv(a, k), bv = dv(b, k);
        if (av === "" && bv === "") return 0;
        if (av === "") return 1;
        if (bv === "") return -1;
        const c = num ? (Number(av) - Number(bv)) || av.localeCompare(bv)
                      : av.localeCompare(bv, undefined, { numeric: true });
        return dir * c;
      });
      all.forEach(tr => tbody.appendChild(tr));
    });
  });
}

/* ------------------------------------------------------------------ line */
async function viewLine(lid) {
  const d = await api("/line/" + encodeURIComponent(lid));
  const l = d.line;
  const scat = Array.isArray(d.state_cat) ? (d.state_cat[0] || "") : (d.state_cat || "");
  const swhy = Array.isArray(d.state_cat) ? (d.state_cat[1] || "") : "";
  main.innerHTML = `
    <div class="pager">
      <a class="btn" href="${d.context.prev ? `#/line/${esc(d.context.prev.line_id)}` : "#"}">${d.context.prev ? "← prev" : "← (start)"}</a>
      <span class="mono">${esc(lid)}</span>
      <a class="btn" href="${d.context.next ? `#/line/${esc(d.context.next.line_id)}` : "#"}">${d.context.next ? "next →" : "(end) →"}</a>
    </div>
    <h1>${esc(d.unit_name)} · line ${esc(lid)}</h1>
    ${stageChain(l.stages, l.stale)}
    ${scat === "needs_revision" ? `<div class="errmsg">⚠ needs revision — ${esc(swhy)}</div>` : ""}
    ${(l.stale || []).length ? `<div class="errmsg">⚠ stale: ${l.stale.join(", ")}</div>` : ""}
    <table class="kv" style="margin-top:10px"><tbody>
      <tr><td>status</td><td>${esc(l.status)}</td></tr>
      <tr><td>release status</td><td>${esc(l.release_status)} ${l.release_note ? `<span class="note">${esc(l.release_note)}</span>` : ""}</td></tr>
      <tr><td>rev / tr_rev / ed_rev</td><td class="mono">${l.rev} / ${l.tr_rev ?? "–"} / ${l.ed_rev ?? "–"}</td></tr>
      <tr><td>source (register)</td><td class="mono">${esc(l.source.file_id)} · ${esc(l.source.scenario_id || l.source.source_id)}</td></tr>
    </tbody></table>
    <h2>Values</h2>
    <div class="fieldrow"><label>RAW (JP source)</label><textarea readonly>${esc(l.raw)}</textarea></div>
    <div class="fieldrow"><label>MTL (machine baseline)</label><textarea readonly>${esc(l.mtl || "")}</textarea></div>
    <div class="fieldrow"><label>TR (translation)</label><textarea id="edit-tr">${esc(l.tr || "")}</textarea></div>
    <div class="fieldrow"><label>ED (edited final)</label><textarea id="edit-ed">${esc(l.ed || "")}</textarea></div>
    <div class="pager">
      <button class="btn primary" id="savevals">Save TR/ED (workflow-checked)</button>
      <button class="btn" id="qc-pass">QC pass</button>
      <button class="btn danger" id="qc-fail">QC fail</button>
    </div>
    <div id="line-msg"></div>
    <h2>Issues on this line</h2>
    <div>${(d.issues || []).map(i => `<span class="pill ${i.status === "reported" ? "needs_revision" : ""}">${esc(i.id)} · ${esc(i.severity)} · ${esc(i.status)}</span>`).join(" ") || '<span class="okmsg">none</span>'}</div>
    <h2>Revisions (${(d.revisions || []).length})</h2>
    <table><thead><tr><th>rev</th><th>stage</th><th>submission</th><th>value (first 80)</th><th>sha10</th><th>note</th></tr></thead><tbody>
      ${(d.revisions || []).map(r => `<tr><td class="mono">${r.rev}</td><td class="stagecell"><b>${esc(r.stage)}</b></td><td class="mono">${esc(r.submission_id || "scene-level")}</td><td class="mono">${esc((r.value || "").slice(0, 80))}</td><td class="mono">${esc(r.sha10 || "")}</td><td class="note">${esc(r.note || "")}</td></tr>`).join("")}
    </tbody></table>
  `;
  const save = POST(`/line/${encodeURIComponent(lid)}`);
  $("#savevals").onclick = async () => {
    const body = { tr: $("#edit-tr").value, ed: $("#edit-ed").value, base_rev: l.rev, actor: "dashboard-user" };
    try {
      const r = await save(body);
      $("#line-msg").innerHTML = r.status === "applied"
        ? `<span class="okmsg">saved → rev ${r.rev_after}. ${(r.effects || []).map(esc).join("<br>")}</span>`
        : `<span class="note">${esc(JSON.stringify(r))}</span>`;
    } catch (e) {
      $("#line-msg").innerHTML = `<span class="errmsg">${esc(e.message)} — the line was changed elsewhere; reload and re-apply.</span>`;
    }
  };
  const qc = POST("/qc");
  $("#qc-pass").onclick = async () => { try { const r = await qc({ line_id: lid, verdict: "pass", actor: "dashboard-user" }); $("#line-msg").innerHTML = `<span class="okmsg">${esc(r.effect)}</span>`; } catch (e) { $("#line-msg").innerHTML = `<span class="errmsg">${esc(e.message)}</span>`; } };
  $("#qc-fail").onclick = async () => { try { const r = await qc({ line_id: lid, verdict: "fail", actor: "dashboard-user" }); $("#line-msg").innerHTML = `<span class="errmsg">${esc(r.effect)}</span>`; } catch (e) { $("#line-msg").innerHTML = `<span class="errmsg">${esc(e.message)}</span>`; } };
}

/* --------------------------------------------------------------- issues */
const ISSUE_FLOW = ["reported", "triaged", "assigned", "correction_required", "verification", "resolved", "closed_invalid", "closed_duplicate", "closed_accepted"];
async function viewIssues() {
  const d = await api("/issues");
  const list = Object.values(d.issues).sort((a, b) => (b.updated_at || "").localeCompare(a.updated_at || ""));
  main.innerHTML = `
    <h1>Issues</h1>
    <div class="fieldrow" style="max-width:700px"><label>Description</label><textarea id="newissue-desc" placeholder="What is wrong / what needs checking?"></textarea></div>
    <div class="filterbar">
      <input type="text" id="newissue-line" placeholder="line_id (optional)" style="width:260px">
      <select id="newissue-sev"><option>Major</option><option selected>Minor</option></select>
      <button class="btn primary" id="newissue-btn">Report issue</button>
    </div>
    <div id="issue-msg"></div>
    <table><thead><tr><th>ID</th><th>Severity</th><th>Status</th><th>Line</th><th>Description</th><th>Updated</th></tr></thead>
    <tbody>${list.map(i => `
      <tr data-iss="${esc(i.id)}" style="cursor:pointer">
        <td class="mono">${esc(i.id)}</td>
        <td class="issue-sev ${esc(i.severity)}">${esc(i.severity)}</td>
        <td><span class="pill ${i.status === "reported" ? "needs_revision" : ""}">${esc(i.status)}</span></td>
        <td class="mono">${i.line_id ? `<a href="#/line/${esc(i.line_id)}">${esc(i.line_id)}</a>` : '<span class="muted">unlinked</span>'}</td>
        <td>${esc((i.description || "").slice(0, 90))}</td>
        <td class="note mono">${esc(i.updated_at || "")}</td>
      </tr>`).join("")}
    </tbody></table>
    <div id="issue-detail"></div>`;
  $("#newissue-btn").onclick = async () => {
    const desc = $("#newissue-desc").value.trim();
    if (!desc) return;
    try {
      const r = await POST("/issues")({ description: desc, line_id: $("#newissue-line").value.trim() || null, severity: $("#newissue-sev").value });
      $("#issue-msg").innerHTML = `<span class="okmsg">created ${esc(r.id)}</span>`;
      viewIssues();
    } catch (e) { $("#issue-msg").innerHTML = `<span class="errmsg">${esc(e.message)}</span>`; }
  };
  $$("#main tr[data-iss]").forEach(tr => tr.onclick = () => showIssueDetail(tr.dataset.iss));
}
async function showIssueDetail(id) {
  const i = await api("/issues/" + encodeURIComponent(id));
  const box = $("#issue-detail");
  if (!box) return;
  box.innerHTML = `
    <h2>${esc(i.id)} — ${esc(i.severity)} · ${esc(i.status)}</h2>
    <p>${esc(i.description)}</p>
    <table class="kv"><tbody>
      <tr><td>line</td><td class="mono">${i.line_id ? `<a href="#/line/${esc(i.line_id)}">${esc(i.line_id)}</a>` : "unlinked"}</td></tr>
      <tr><td>reported by</td><td>${esc(i.reported_by || "")}</td></tr>
      <tr><td>history</td><td>${(i.history || []).map(h => `<div class="note">${esc(h.ts)} ${esc(h.action)} ${h.note ? "— " + esc(h.note) : ""}</div>`).join("")}</td></tr>
    </tbody></table>
    <div class="filterbar">
      <select id="iss-status">${ISSUE_FLOW.map(s => `<option ${s === i.status ? "selected" : ""}>${s}</option>`).join("")}</select>
      <input type="text" id="iss-reason" placeholder="reason / note">
      <button class="btn primary" id="iss-setstatus">Set status</button>
      <input type="text" id="iss-link" placeholder="link line_id" style="width:220px">
      <button class="btn" id="iss-link-btn">Link line</button>
    </div>`;
  $("#iss-setstatus").onclick = async () => { await POST(`/issues/${encodeURIComponent(id)}/status`)({ status: $("#iss-status").value, reason: $("#iss-reason").value }); viewIssues(); showIssueDetail(id); };
  $("#iss-link-btn").onclick = async () => { try { await POST(`/issues/${encodeURIComponent(id)}/link`)({ line_id: $("#iss-link").value.trim() }); showIssueDetail(id); } catch (e) { alert(e.message); } };
}

/* -------------------------------------------------------------- imports */
async function viewImports() {
  const d = await api("/imports");
  main.innerHTML = `
    <h1>Imports</h1>
    <p class="note">Drop files into <span class="mono">imports/incoming/</span> (CSV/TSV/JSON, UTF-8). The dashboard never accepts an import without preview + apply.</p>
    <div class="pager"><button class="btn primary" id="scanbtn">Scan incoming/</button></div>
    <div id="import-msg"></div>
    <table><thead><tr><th>ID</th><th>File</th><th>Status</th><th>Rows</th><th>Counts</th><th>Applied as</th></tr></thead>
    <tbody>${Object.values(d.imports).map(x => `
      <tr data-imp="${esc(x.id)}" style="cursor:pointer">
        <td class="mono">${esc(x.id)}</td><td class="mono">${esc(x.filename)}</td>
        <td><span class="pill ${x.status === "pending" ? "awaiting_qc" : x.status === "applied" ? "final" : ""}">${esc(x.status)}</span></td>
        <td>${x.rows_total || ""}</td>
        <td class="mono note">${Object.entries(x.preview_counts || {}).map(([k, v]) => `${k}:${v}`).join(" ")}</td>
        <td class="mono">${esc(x.applied_as_sub || "")}</td>
      </tr>`).join("") || `<tr><td colspan=6 class="muted">no imports yet</td></tr>`}
    </tbody></table>
    <div id="import-preview"></div>`;
  $("#scanbtn").onclick = async () => { const r = await POST("/imports/scan")({}); $("#import-msg").innerHTML = r.found.length ? `<span class="okmsg">found ${r.found.join(", ")}</span>` : '<span class="note">nothing new</span>'; viewImports(); };
  $$("#main tr[data-imp]").forEach(tr => tr.onclick = async () => {
    const id = tr.dataset.imp;
    try {
      const p = await api(`/imports/${encodeURIComponent(id)}/preview`);
      $("#import-preview").innerHTML = `
        <h2>Preview ${esc(id)}</h2>
        <p class="mono note">${Object.entries(p.counts || {}).map(([k, v]) => `${k}: ${v}`).join(" · ")}</p>
        ${(p.errors || []).map(e => `<div class="errmsg">${esc(e)}</div>`).join("")}
        <table><thead><tr><th>row</th><th>line_id</th><th>match</th><th>changes</th><th>workflow effects</th></tr></thead><tbody>
          ${(p.results || []).slice(0, 100).map(r => `<tr>
            <td class="mono">${r.row_no}</td>
            <td class="mono">${esc(r.line_id || "")}</td>
            <td><span class="pill ${r.match === "modified" ? "awaiting_qc" : r.match === "unchanged" ? "final" : ""}">${esc(r.match)}</span></td>
            <td class="mono note">${Object.keys(r.changes || {}).map(k => `${k}: ${(r.changes[k].old || "").slice(0, 25)} → ${(r.changes[k].new || "").slice(0, 25)}`).join("<br>")}</td>
            <td class="note">${(r.effects || []).map(esc).join("<br>")}</td>
          </tr>`).join("")}
        </tbody></table>
        ${p.results && p.results.length > 100 ? `<p class="note">… ${p.results.length - 100} more rows</p>` : ""}
        <div class="pager">
          <button class="btn primary" id="imp-apply">Apply (creates submission)</button>
          <button class="btn danger" id="imp-reject">Reject</button>
        </div>`;
      $("#imp-apply").onclick = async () => { try { const r = await POST(`/imports/${encodeURIComponent(id)}/apply`)({}); $("#import-msg").innerHTML = `<span class="okmsg">applied as ${esc(r.submission_id)} (${r.lines_applied} lines)</span>`; viewImports(); } catch (e) { $("#import-msg").innerHTML = `<span class="errmsg">${esc(e.message)}</span>`; } };
      $("#imp-reject").onclick = async () => { await POST(`/imports/${encodeURIComponent(id)}/reject`)({ note: "rejected from dashboard" }); viewImports(); };
    } catch (e) { $("#import-preview").innerHTML = `<div class="errmsg">${esc(e.message)}</div>`; }
  });
}

/* ------------------------------------------------------------- releases */
async function viewReleases() {
  const r = await api("/releases");
  main.innerHTML = `
    <h1>Releases</h1>
    <p class="note">Release artifacts are generated by scripts, never hand-edited. This page views them and can run the acceptance gate.</p>
    <h2>Catalog (approved final set)</h2>
    ${r.catalog ? `<table class="kv"><tbody>
      <tr><td>generated</td><td class="mono">${esc(r.catalog.generated_at_utc)}</td></tr>
      <tr><td>DLL changed strings</td><td>${r.catalog.dll_entries}</td></tr>
      <tr><td>asset changed fields</td><td>${r.catalog.asset_entries}</td></tr>
      <tr><td>changed data files</td><td>${r.catalog.changed_data_files}</td></tr>
    </tbody></table>` : '<span class="errmsg">catalog missing</span>'}
    <h2>state/ files</h2>
    <table><thead><tr><th>file</th><th>sha256</th><th>size</th></tr></thead><tbody>
      ${r.state_files.map(f => `<tr><td class="mono">${esc(f.name)}</td><td class="mono">${esc(f.sha256)}</td><td>${f.size}</td></tr>`).join("")}
    </tbody></table>
    <h2>Patcher</h2>
    ${r.patcher ? `<p class="mono note">${esc(r.patcher.path)}<br>sha256: ${esc(r.patcher.sha256)}</p>` : '<span class="note">05. patcher/patcher.py not found yet (A9 pending)</span>'}
    <h2>Acceptance gate</h2>
    <div class="pager"><button class="btn primary" id="runacc">Run acceptance tests</button></div>
    <div id="acc-out">${r.acceptance ? `<p class="${r.acceptance.exit_code === 0 ? "okmsg" : "errmsg"}">last run ${esc(r.acceptance.ts)}: exit ${r.acceptance.exit_code}</p><pre class="mono-block">${(r.acceptance.tail || []).map(esc).join("\n")}</pre>` : '<span class="note">not run from dashboard yet</span>'}</div>`;
  $("#runacc").onclick = async () => {
    $("#acc-out").innerHTML = '<span class="note">running… (takes a minute or two)</span>';
    try {
      const r2 = await POST("/releases/run_acceptance")({});
      $("#acc-out").innerHTML = `<p class="${r2.exit_code === 0 ? "okmsg" : "errmsg"}">exit ${r2.exit_code} @ ${esc(r2.ts)}</p><pre class="mono-block">${(r2.tail || []).map(esc).join("\n")}</pre>`;
    } catch (e) { $("#acc-out").innerHTML = `<span class="errmsg">${esc(e.message)}</span>`; }
  };
}

/* --------------------------------------------------------------- router */
const routes = [
  [/^#\/unit\/(.+)$/, viewUnit],
  [/^#\/line\/(.+)$/, viewLine],
];
async function route() {
  const h = location.hash || "#/project";
  for (const [re, fn] of routes) {
    const m = h.match(re);
    if (m) { try { await fn(decodeURIComponent(m[1])); } catch (e) { main.innerHTML = `<div class="errmsg">${esc(e.message)}</div>`; } return; }
  }
  const page = h.replace(/^#\//, "").split("?")[0];
  const views = { project: viewProject, units: viewUnits, lines: viewLines, issues: viewIssues, imports: viewImports, releases: viewReleases };
  try { await (views[page] || viewProject)(); } catch (e) { main.innerHTML = `<div class="errmsg">${esc(e.message)}</div>`; }
  $$("#mainnav a").forEach(a => a.classList.toggle("active", "#" + a.dataset.nav === h.split("?")[0].replace(/^#/, "#") || "/" + a.dataset.nav === "/" + page));
}

/* ------------------------------------------------------ global search */
const gs = $("#globalsearch");
gs.addEventListener("keydown", async (ev) => {
  if (ev.key !== "Enter") return;
  const q = gs.value.trim();
  if (!q) return;
  try {
    const res = await api("/search?q=" + encodeURIComponent(q));
    const box = $("#searchresults");
    if (!res.length) { box.innerHTML = `<div class="sr-item muted">no matches</div>`; box.classList.remove("hidden"); return; }
    box.innerHTML = res.map(r => `<div class="sr-item" data-lid="${esc(r.line_id)}">
      <span class="mono">${esc(r.line_id)}</span> <span class="note">${r.matched_fields.join("/")}</span><br>
      <span class="muted">${esc(r.raw || "")}</span><br>${esc(r.ed || r.tr || "")}</div>`).join("");
    box.classList.remove("hidden");
    $$("#searchresults .sr-item[data-lid]").forEach(el => el.onclick = () => { location.hash = `#/line/${el.dataset.lid}`; });
  } catch (e) { console.error(e); }
});
document.addEventListener("click", e => { if (!e.target.closest(".searchbox")) $("#searchresults").classList.add("hidden"); });

window.addEventListener("hashchange", route);
route();
